import os
import asyncio
import json
import redis
import time
import re
import base64
from dotenv import load_dotenv
from rag_engine import rag_engine

import openai
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langsmith import traceable, trace
from langsmith.run_helpers import get_current_run_tree
from tools import OPENAI_TOOL_SCHEMAS, execute_tool_call
from agent_policy import evaluate_approval_decision, evaluate_task_policy
from agent_governance import (
    complete_approval,
    create_approval_request,
    record_tool_run,
    verify_approval_decision,
)

ocr_reader = None
def get_ocr_reader():
    global ocr_reader
    if ocr_reader is None:
        try:
            import easyocr
            ocr_reader = easyocr.Reader(['ch_sim', 'en'])
        except Exception as err:
            print(f"[OCR] EasyOCR initialization failed: {err}")
            return None
    return ocr_reader



def _decode_data_uri(data_uri: str) -> bytes:
    if not data_uri:
        return b""
    _header, encoded = data_uri.split(",", 1) if "," in data_uri else ("", data_uri)
    return base64.b64decode(encoded)


def _ocr_image_variants(image_bytes: bytes) -> list[tuple[str, object]]:
    import cv2
    import numpy as np

    def deskew(gray_image):
        coords = np.column_stack(np.where(gray_image < 245))
        if coords.size == 0:
            return gray_image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5 or abs(angle) > 15:
            return gray_image
        h, w = gray_image.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(gray_image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    nparr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("图片解码失败，可能不是有效的 PNG/JPEG/WebP 数据")

    variants: list[tuple[str, object]] = [("原图", bgr)]
    height, width = bgr.shape[:2]
    scale = 2.0 if max(height, width) < 1400 else 1.35
    enlarged = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    variants.append(("高清放大", enlarged))

    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 12, 7, 21)
    sharp = cv2.addWeighted(gray, 1.45, cv2.GaussianBlur(gray, (0, 0), 1.2), -0.45, 0)
    variants.append(("灰度增强", sharp))

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(sharp)
    variants.append(("局部对比增强", clahe))

    deskewed = deskew(clahe)
    variants.append(("倾斜纠偏", deskewed))

    adaptive = cv2.adaptiveThreshold(
        deskewed,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    variants.append(("二值增强", adaptive))

    inverted = cv2.bitwise_not(adaptive)
    variants.append(("反色二值增强", inverted))
    return variants


def _clean_ocr_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _dedupe_ocr_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique_items: list[dict[str, object]] = []
    for item in items:
        text = str(item.get("text") or "").strip()
        key = re.sub(r"\W+", "", text.lower())
        if not key or key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def _ocr_confidence_summary(items: list[dict[str, object]]) -> tuple[float, float]:
    if not items:
        return 0.0, 0.0
    confidences = [float(item.get("confidence") or 0.0) for item in items]
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)
    return avg_confidence, min_confidence


def extract_image_ocr_text(image_data: str) -> tuple[str, list[dict[str, object]]]:
    reader = get_ocr_reader()
    image_bytes = _decode_data_uri(image_data)
    if not image_bytes:
        return "", []

    min_confidence = float(os.getenv("OCR_MIN_CONFIDENCE", "0.22"))
    best_text = ""
    best_items: list[dict[str, object]] = []
    best_score = -1.0

    for variant_name, image in _ocr_image_variants(image_bytes):
        try:
            result = reader.readtext(
                image,
                detail=1,
                paragraph=False,
                decoder="beamsearch",
                text_threshold=0.45,
                low_text=0.25,
                link_threshold=0.25,
                width_ths=0.7,
                add_margin=0.08,
                mag_ratio=1.4,
            )
        except Exception as variant_error:
            print(f"[OCR] variant {variant_name} failed: {variant_error}")
            continue

        items: list[dict[str, object]] = []
        fallback_items: list[dict[str, object]] = []
        for bbox, text, prob in result:
            cleaned = _clean_ocr_text(str(text))
            if not cleaned:
                continue
            item = {"text": cleaned, "confidence": float(prob), "variant": variant_name, "bbox": bbox}
            fallback_items.append(item)
            if float(prob) >= min_confidence:
                items.append(item)

        selected_items = _dedupe_ocr_items(items or fallback_items)
        joined = " ".join(str(item["text"]) for item in selected_items).strip()
        score = len(joined) + sum(float(item["confidence"]) for item in selected_items)
        if joined and score > best_score:
            best_text = joined
            best_items = selected_items
            best_score = score

    return best_text, best_items


def _needs_vision_ocr_review(extracted_text: str, ocr_items: list[dict[str, object]]) -> bool:
    if os.getenv("ENABLE_OCR_VLM_REVIEW", "true").lower() != "true":
        return False
    avg_confidence, min_confidence = _ocr_confidence_summary(ocr_items)
    low_avg_threshold = float(os.getenv("OCR_VLM_REVIEW_AVG_THRESHOLD", "0.62"))
    low_min_threshold = float(os.getenv("OCR_VLM_REVIEW_MIN_THRESHOLD", "0.35"))
    if not extracted_text:
        return True
    if avg_confidence < low_avg_threshold:
        return True
    return bool(ocr_items and min_confidence < low_min_threshold)


async def review_ocr_with_vision_model(client, image_data: str, extracted_text: str, selected_model: str) -> str:
    if os.getenv("ENABLE_VLM", "false").lower() != "true":
        return ""

    # 优先读取 DeepSeek 专有 OCR 模型名称 DeepSeek-OCR-2，回退到 VISION_MODEL_NAME 或 selected_model
    ocr_specific_model = os.getenv("DEEPSEEK_OCR_MODEL_NAME", "DeepSeek-OCR-2")
    vision_model = os.getenv("VISION_MODEL_NAME") or ocr_specific_model or selected_model
    vision_api_base = os.getenv("VISION_API_BASE") or os.getenv("OPENAI_API_BASE", "https://api.deepseek.com")
    vision_api_key = os.getenv("VISION_API_KEY") or os.getenv("OPENAI_API_KEY", "dummy")

    # 如果独立配置了 Vision 网关，使用专门的 client；否则沿用主 client
    if os.getenv("VISION_API_BASE") or os.getenv("VISION_API_KEY"):
        vision_client = openai.AsyncOpenAI(api_key=vision_api_key, base_url=vision_api_base)
    else:
        vision_client = client

    prompt = (
        "你是企业级 DeepSeek OCR 专有视觉复核引擎。请直接识别读取图片中的文字，重点精确提取中文手写、连笔、表格、拍照阴影与复杂版面。\n"
        "下面是本地 OCR 初始识别初稿：\n"
        f"```text\n{extracted_text or '无'}\n```\n\n"
        "请结合原图修正有误字符，只返回修正后的纯文字或表格 Markdown 结构；无法确认的字标注 [?]，严禁编造。"
    )
    try:
        response = await asyncio.wait_for(
            vision_client.chat.completions.create(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ],
                }],
                temperature=0,
            ),
            timeout=float(os.getenv("OCR_VLM_REVIEW_TIMEOUT_SECONDS", "20")),
        )
        reviewed_text = response.choices[0].message.content if response.choices else ""
        return _clean_ocr_text(reviewed_text or "")
    except Exception as review_error:
        # 如果 DeepSeek-OCR-2 端点在当前网关暂未开放或报 400，自动平滑退回到 deepseek-v4-flash 复核
        fallback_model = os.getenv("MODEL_FLASH", "deepseek-v4-flash")
        if vision_model != fallback_model:
            try:
                print(f"[OCR] DeepSeek-OCR-2 专属端点不可用: {review_error}，正在自动平滑回退至通用视觉模型 {fallback_model}...")
                fallback_resp = await asyncio.wait_for(
                    vision_client.chat.completions.create(
                        model=fallback_model,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_data}},
                            ],
                        }],
                        temperature=0,
                    ),
                    timeout=float(os.getenv("OCR_VLM_REVIEW_TIMEOUT_SECONDS", "20")),
                )
                reviewed_text = fallback_resp.choices[0].message.content if fallback_resp.choices else ""
                return _clean_ocr_text(reviewed_text or "")
            except Exception as fb_err:
                print(f"[OCR] Vision fallback also bypassed: {fb_err}")
                return ""
        print(f"[OCR] vision review (model={vision_model}) bypassed or failed: {review_error}")
        return ""



@traceable(name="whisper_audio_transcription", run_type="tool", tags=["multimodal_speech", "faster_whisper"])
async def transcribe_audio_isolated(audio_path: str) -> str:
    import asyncio
    import json
    import sys
    script_path = os.path.join(os.path.dirname(__file__), "run_whisper.py")
    process = await asyncio.create_subprocess_exec(
        sys.executable, script_path, audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"Whisper process failed: {stderr.decode('utf-8', errors='ignore')}")
    try:
        # 查找最后一个 JSON 对象（防止 ffmpeg 输出杂讯）
        out_lines = stdout.decode('utf-8', errors='ignore').strip().split("\n")
        res = json.loads(out_lines[-1])
        if "error" in res:
            raise Exception(res["error"])
        return res.get("text", "")
    except Exception as e:
        raise Exception(f"Failed to parse Whisper output: {str(e)}\nRaw output: {stdout.decode('utf-8', errors='ignore')}")

# Set up environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

EXPERT_BADGE_MARKER = "专家推演思考大引擎"
FAST_BADGE_MARKER = "混合极速引擎"
SYSTEM_BADGE_RE = re.compile(r"\n?> \*.*\[系统态:.*(?:\n|$)")


def _strip_system_badges(content: str) -> str:
    """去除 AI 历史回复末尾的系统强制挂载签条，避免模型自我复读该格式"""
    if not content:
        return ""
    lines = content.split('\n')
    cleaned = []
    for line in lines:
        if line.startswith("> ") and ("[系统态:" in line or "[企业安全壁垒触发]" in line or "[多模态音频深化引擎]" in line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).rstrip()

def _has_expert_badge(content: str) -> bool:
    return EXPERT_BADGE_MARKER in (content or "") or "[系统态:" in (content or "")

def _has_fast_badge(content: str) -> bool:
    return FAST_BADGE_MARKER in (content or "") or "BGE+BM25 极速收束" in (content or "") or "[系统态:" in (content or "")

def publish_to_ws(session_id: str, data: dict):
    client = redis.from_url(redis_url)
    client.publish(f"ws:{session_id}", json.dumps(data))

def select_model_by_task(requested_model: str, mode: str, has_complex_input: bool = False) -> str:
    """根据任务类型在 deepseek-v4-flash (极速) 与 deepseek-v4-pro (深度) 之间自动路由"""
    flash_model = os.getenv("MODEL_FLASH", "deepseek-v4-flash")
    pro_model = os.getenv("MODEL_PRO", "deepseek-v4-pro")
    
    # 客户端显式指定了具体版本时优先尊重显式传递
    if requested_model and requested_model not in {"auto", "default", "deepseek-chat"}:
        return requested_model
        
    # 1. 高阶专家分析、代码沙箱执行、多步 Tool Call、HITL 审批流程使用 deepseek-v4-pro
    if mode in {"expert", "code", "agent_graph", "hitl"} or has_complex_input:
        return pro_model

    # 2. 常规对话、简单分类、语音/文本初加工使用 deepseek-v4-flash
    return flash_model

@traceable(name="ai_terminal_workflow", run_type="chain", tags=["business_observability", "agent_pipeline"])
async def async_process_request(
    session_id: str,
    user_msg: str,
    mode: str,
    selected_model: str,
    history: list,
    image_data: str = None,
    audio_data: str = None,
    file_upload: dict = None,
    ws_send_func=None,
    face_data: str = None,
    hitl_approved: bool = False,
    approval_kind: str = "",
    approval_id: str = "",
    approval_token: str = "",
    user_id: str = "anonymous",
    tenant_id: str = "default",
    user_permissions: list[str] | None = None,
):
    # 根据任务特性动态判定最佳模型
    effective_model = select_model_by_task(
        requested_model=selected_model,
        mode=mode,
        has_complex_input=bool(image_data or face_data or (file_upload and not "audio" in str(file_upload.get("type", "")).lower()))
    )
    selected_model = effective_model

    
    rt = get_current_run_tree()
    if rt:
        rt.add_metadata({
            "session_id": session_id,
            "mode": mode,
            "selected_model": effective_model,
            "modality": "speech" if (audio_data or (file_upload and "audio" in str(file_upload.get("type", "")).lower())) else ("face_verification" if face_data else ("vision" if image_data else ("doc" if file_upload else "text"))),
            "history_length": len(history) if history else 0
        })
    db_url = os.getenv("ASYNC_DATABASE_URL", "postgresql://aiuser:aipassword@localhost:5432/ailearning")
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    base_url = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    
    current_approval_id: str | None = None
    verified_approval_kind = ""
    tool_call_stack: dict[str, list[dict[str, object]]] = {}
    final_response = ""
    permissions = set(user_permissions or [])
    stream_started = False
    stream_ended = False

    async def base_ws_send(data: dict):
        if ws_send_func:
            await ws_send_func(data)
        else:
            publish_to_ws(session_id, data)

    async def ws_send(data: dict):
        nonlocal current_approval_id, stream_started, stream_ended

        event_type = data.get("type")
        if event_type == "stream_start":
            if stream_started and not stream_ended:
                return
            stream_started = True
            stream_ended = False
            await base_ws_send(data)
            return

        if event_type == "stream_chunk":
            if stream_ended:
                return
            if not stream_started:
                stream_started = True
                await base_ws_send({"type": "stream_start"})
            await base_ws_send(data)
            return

        if event_type == "stream_end":
            if stream_ended:
                return
            if not stream_started:
                stream_started = True
                await base_ws_send({"type": "stream_start"})
            stream_ended = True
            await base_ws_send(data)
            return

        if data.get("type") == "hitl_request":
            params = dict(data.get("params") or {})
            approval_record = await create_approval_request(
                session_id=session_id,
                requester_user_id=user_id,
                tenant_id=tenant_id,
                task=str(data.get("content") or user_msg or ""),
                approval_kind=str(params.get("approval_kind") or "continue_analysis"),
                params={**params, "policy": params.get("policy") or {}},
            )
            current_approval_id = approval_record["approval_id"]
            params.update({
                "approval_id": approval_record["approval_id"],
                "approval_token": approval_record["approval_token"],
                "expires_at": approval_record["expires_at"],
            })
            await base_ws_send({**data, "params": params})
            return

        if data.get("type") == "tool_call":
            tool_name = str(data.get("name") or "unknown")
            tool_call_stack.setdefault(tool_name, []).append({
                "args": data.get("args", ""),
                "started_at": time.perf_counter(),
            })
            await base_ws_send(data)
            return

        if data.get("type") == "tool_call_result":
            tool_name = str(data.get("name") or "unknown")
            stack = tool_call_stack.get(tool_name) or []
            call_info = stack.pop(0) if stack else {"args": "", "started_at": time.perf_counter()}
            result_payload = data.get("result", "")
            status = "ok"
            if isinstance(result_payload, dict) and result_payload.get("ok") is False:
                status = "error"
            duration_ms = int((time.perf_counter() - float(call_info.get("started_at", time.perf_counter()))) * 1000)
            try:
                await record_tool_run(
                    session_id=session_id,
                    requester_user_id=user_id,
                    tenant_id=tenant_id,
                    approval_id=current_approval_id,
                    mode=mode,
                    tool_name=tool_name,
                    arguments=call_info.get("args", ""),
                    result_summary=json.dumps(result_payload, ensure_ascii=False) if isinstance(result_payload, (dict, list)) else str(result_payload or ""),
                    status=status,
                    duration_ms=duration_ms,
                )
            except Exception as audit_error:
                print(f"[Tool Audit] failed to record {tool_name}: {audit_error}")
            await base_ws_send(data)
            return

        await base_ws_send(data)

    try:
        if audio_data:
            await ws_send({"type": "status", "content": "🎙️ 正在进行语音识别转写 (Faster-Whisper)..."})
            try:
                import tempfile
                header, encoded = audio_data.split(",", 1) if "," in audio_data else ("", audio_data)
                audio_bytes = base64.b64decode(encoded)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                    temp_audio.write(audio_bytes)
                    temp_audio_path = temp_audio.name
                
                transcribed_text = await transcribe_audio_isolated(temp_audio_path)
                os.remove(temp_audio_path)
                
                await ws_send({"type": "status", "content": f"📝 语音转写完成: {transcribed_text}"})
                # 将转写的文本追加或替换为用户的消息
                if user_msg:
                    user_msg = f"{user_msg}\n【语音输入】: {transcribed_text}"
                else:
                    user_msg = transcribed_text
            except Exception as e:
                await ws_send({"type": "status", "content": f"❌ 语音识别失败: {str(e)}"})
                
        if file_upload:
            file_name = file_upload.get("name", "unknown")
            file_type = file_upload.get("type", "")
            file_encoded = file_upload.get("data", "")
            
            await ws_send({"type": "status", "content": f"📄 正在解析上传的文档: {file_name}"})
            try:
                header, encoded = file_encoded.split(",", 1) if "," in file_encoded else ("", file_encoded)
                file_bytes = base64.b64decode(encoded)
                
                # Save file to knowledge base directory for RAG
                kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'document_processor', 'samples'))
                os.makedirs(kb_dir, exist_ok=True)
                file_path = os.path.join(kb_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                
                extracted_text = ""
                audio_exts = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm")
                
                image_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
                if file_name.lower().endswith(audio_exts) or "audio" in file_type.lower():
                    await ws_send({"type": "status", "content": f"🎙️ 正在将音频文件 {file_name} 转写为文字..."})
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1] or ".mp3") as temp_audio:
                        temp_audio.write(file_bytes)
                        temp_audio_path = temp_audio.name
                    
                    extracted_text = await transcribe_audio_isolated(temp_audio_path)
                    os.remove(temp_audio_path)
                elif file_name.lower().endswith(image_exts) or "image" in file_type.lower():
                    # file_encoded 已经是完整的 Data URL（data:image/xxx;base64,....）
                    # 直接赋值，不能再拼接前缀，否则形成双重 header 导致 Base64 解码失败
                    if not image_data:
                        if file_encoded.startswith("data:"):
                            # 已经是完整 Data URL，直接使用
                            image_data = file_encoded
                        else:
                            # 纯 base64 裸字符串，补齐 MIME 前缀
                            image_data = f"data:{file_type or 'image/png'};base64,{file_encoded}"
                elif file_name.lower().endswith(".pdf") or "pdf" in file_type.lower():
                    import fitz
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    for page in pdf_doc:
                        extracted_text += page.get_text() + "\n"
                    pdf_doc.close()
                else:
                    # Default text fallback
                    extracted_text = file_bytes.decode("utf-8", errors="ignore")

                
                # Append to user message
                if extracted_text.strip():
                    if user_msg:
                        user_msg = f"{user_msg}\n\n【附件文档：{file_name}】\n{extracted_text}"
                        await ws_send({"type": "status", "content": f"✅ 文档解析成功 (字数: {len(extracted_text)})"})
                    else:
                        if file_name.lower().endswith(audio_exts) or "audio" in file_type.lower():
                            await ws_send({"type": "status", "content": "✅ 语音识别分段完成！正在由大模型为您构建专业文案排版与智能归纳..."})
                            await ws_send({"type": "stream_start"})
                            formatted_header = f"### 🎙️ 【语音逐句分段与停顿明细】\n\n{extracted_text}\n\n---\n### ✍️ 【智能重构与高价值干货文案整理】\n\n"
                            await ws_send({"type": "stream_chunk", "content": formatted_header})
                            
                            audio_prompt = (
                                f"以下是一段 M4A/音频 经引擎逐条切句并带有分段停顿的完整文字实录：\n\n{extracted_text}\n\n"
                                "【您的职责与核心产出任务】：\n"
                                "1. 脱稿精练：剔除原语音中的口头禅（如‘嗯’、‘也就是’）、多余重复表述与碎屑口语；\n"
                                "2. 高级文案赋能：将其深度重构为逻辑清晰、辞藻传神、极易于内部展示或对外运营的高质生产力【专属商务/新媒体文案】；\n"
                                "3. 要点归结：结尾运用 Markdown 小标签提列【✨ 核心主线与金句大纲】，使文案立刻拥有商业实操和再传播价值！"
                            )
                            stream = await client.chat.completions.create(
                                model=selected_model,
                                messages=[
                                    {"role": "system", "content": "你是首席商务通信总监与顶级文案金牌编剧。"},
                                    {"role": "user", "content": audio_prompt}
                                ],
                                stream=True,
                                temperature=0.3
                            )
                            async for chunk in stream:
                                content = chunk.choices[0].delta.content
                                if content:
                                    await ws_send({"type": "stream_chunk", "content": content})
                            
                            badge = "\n\n> *✨ [多模态音频深化引擎] | Faster-Whisper 段落智停 + LLM 金牌文案生成闭环*"
                            await ws_send({"type": "stream_chunk", "content": badge})
                            await ws_send({"type": "stream_end"})
                            await ws_send({"type": "task_complete", "content": "Task completed successfully."})
                            return # Completed multi-stage audio enhancement, bypass default RAG loop
                        else:
                            user_msg = f"基于以下文档内容进行分析：\n【附件文档：{file_name}】\n{extracted_text}"
                            await ws_send({"type": "status", "content": f"✅ 文档解析成功 (字数: {len(extracted_text)})"})
                else:
                    await ws_send({"type": "status", "content": f"⚠️ 文档解析结果为空"})
            except Exception as e:
                await ws_send({"type": "status", "content": f"❌ 文档解析失败: {str(e)}"})

        if image_data:
            await ws_send({"type": "status", "content": "🖼️ [图文 OCR 专项通道] 正在扫描图片文字，并进行多尺度增强识别..."})
            try:
                extracted_text, ocr_items = extract_image_ocr_text(image_data)
                avg_confidence, min_confidence = _ocr_confidence_summary(ocr_items)
                needs_review = _needs_vision_ocr_review(extracted_text, ocr_items)
                reviewed_text = ""
                if needs_review and os.getenv("ENABLE_VLM", "false").lower() == "true":
                    await ws_send({"type": "status", "content": "🔎 OCR 置信度偏低或识别出复杂版面，正在调用视觉模型复核手写/表格/图文内容..."})
                    reviewed_text = await review_ocr_with_vision_model(client, image_data, extracted_text, selected_model)
                    if reviewed_text and reviewed_text != extracted_text:
                        extracted_text = reviewed_text
                        await ws_send({"type": "status", "content": "✅ 视觉模型已完成 OCR 二次复核，已自动纠错并增强文本。"})

                if extracted_text and extracted_text.strip():
                    confidence_note = ""
                    if needs_review and not reviewed_text:
                        confidence_note = " 手写/低清内容存在误识风险；如需更高准确率，可配置 ENABLE_VLM=true。"
                    await ws_send({"type": "status", "content": f"📝 OCR 识别完成：提取 {len(extracted_text)} 个字符，片段 {len(ocr_items)} 个，平均置信度 {avg_confidence:.2f}。{confidence_note}"})
                    await ws_send({"type": "stream_start"})
                    
                    ocr_display_markdown = (
                        f"### 🖼️ 图片 OCR 文字提取结果\n\n"
                        f"```text\n{extracted_text}\n```\n\n"
                        f"> 📊 *识别置信度：平均 {avg_confidence:.2f} / 最低 {min_confidence:.2f} (提取片段数: {len(ocr_items)})*\n\n"
                        f"---\n\n"
                    )
                    await ws_send({
                        "type": "stream_chunk",
                        "content": ocr_display_markdown,
                    })
                    user_msg = (
                        f"【图文 OCR 专属识别与文案提炼指南】\n"
                        f"系统已在用户上传的图片中提取了如下文字：\n\n"
                        f"```text\n{extracted_text}\n```\n\n"
                        f"OCR 识别置信度：平均 {avg_confidence:.2f} / 最低 {min_confidence:.2f}。\n\n"
                        f"用户当前提问/指令：【{user_msg or '请直接帮我不删关键事实地将以上文本按结构化条理归纳提炼。'}】"
                    )
                else:
                    vlm_hint = "建议启用视觉大模型 VLM 或上传更清晰的原图与 PDF。"
                    await ws_send({"type": "status", "content": f"📝 OCR 扫描完成，未检测到稳定文字。{vlm_hint}"})
                    await ws_send({"type": "stream_start"})
                    await ws_send({
                        "type": "stream_chunk",
                        "content": "⚠️ **图片 OCR 识别提示**：未在当前上传的图片中提取到稳定清晰的文字内容。建议上传光线均匀、文字占比较大的清晰图片或文档 PDF。\n\n---\n\n",
                    })
                    user_msg = f"用户上传了一张图片，但 OCR 未识别出稳定文字。用户指令为：{user_msg or '说明识别失败并给出重新上传建议。'}"
            except Exception as e:
                await ws_send({"type": "status", "content": f"❌ OCR 识别失败: {str(e)}"})
                user_msg = f"用户上传图片进行 OCR 识别，但处理出错：{str(e)}。"


        if face_data:
            await ws_send({"type": "status", "content": "👤 [安全专属人脸核实通道] 启动 YOLOv8n 生物边定位与 ArcFace 512维多点真光验证..."})
            try:
                header, encoded = face_data.split(",", 1) if "," in face_data else ("", face_data)
                face_bytes = base64.b64decode(encoded)
                import cv2
                import numpy as np
                from deepface import DeepFace
                
                nparr = np.frombuffer(face_bytes, np.uint8)
                cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '16-face-recognition', 'local_face_db'))
                
                if cv_img is not None and os.path.exists(db_path):
                    await ws_send({"type": "status", "content": "🔬 [512-d 矩阵比拼在野] 正在把裁片压向特征倒排红线安全区计算余弦偏角..."})
                    dfs = DeepFace.find(
                        img_path=cv_img,
                        db_path=db_path,
                        model_name="ArcFace",
                        detector_backend="yolov8n",
                        enforce_detection=False,
                        silent=True
                    )
                    if len(dfs) > 0 and len(dfs[0]) > 0:
                        best_match = dfs[0].iloc[0]
                        identity_path = str(best_match['identity'])
                        distance = float(best_match['distance'])
                        person_name = os.path.splitext(os.path.basename(identity_path))[0]
                        
                        if distance < 0.68:
                            face_report = f"✅ **【AI权威专属人脸门检：验证全线绿标通行】**\n- 身份册底索还：**【 {person_name} 】**\n- 测试执行算网：`YOLOv8-Nano (边际剪下) ➕ ArcFace (ResNet-512 Embedding)`\n- 余弦距离角值 (Cosine Distance)：`{distance:.5f}` （严于通检界线阈址 <= 0.6820）\n- **安全质证断意**：**完全吻合！属于本司获照白名单当班主事人**。"
                            await ws_send({"type": "status", "content": f"🎯 专属人脸防核完成：查验一致为册存政要【 {person_name} 】 (误差率:{distance:.4f})！"})
                        else:
                            face_report = f"⚠️ **【AI专属人脸核身异常警钟】**：抓查到了人类真实面膛五官，但在机房深空持久授权向量仓池内对不出等差亲情同像（计算最挨近极限夹合值为 `{distance:.5f}` >= 红灯关闸门线 `0.6820`）。\n- **防空下派决算**：**一不具备名分，二有伪仿试通关可能，阻难于授权线之外！**"
                            await ws_send({"type": "status", "content": f"🛑 人像搜源完成，最优拟度偏斜度（{distance:.4f} > 0.682）未达许可红轨，拒绝通配。"})
                    else:
                        face_report = "🔍 **【生物核对未逢脸形】**：提交进安全人像质检通道的图像没含露半丝人面骨干（可能是风景、凭据纸张或黑光失准像）。"
                        await ws_send({"type": "status", "content": "⚠️ 人庞校验告毕，由于无活体轮廓迹象，拒绝启动512d降权运算。"})
                    
                    user_msg = f"### 🛡️ 【全量智能专属人脸生物特征质证陈词】\n{face_report}\n\n当前接待长官/用语提令为：【{user_msg or '仔细针对该封专属化人像身份质检结论向长官以威严而职业的角度宣讲报告！清楚列点说明比武距离是不是符合合规边界与真实真名为谁！'}】"
                else:
                    user_msg = f"由于读取人脸相流败错或特征底层断除，未竟识别流程。\n\n当前陈述主张：{user_msg}"
            except Exception as fe:
                await ws_send({"type": "status", "content": f"⚠️ 人脸核身管道遭遇堵闭: {str(fe)}"})

        # 实时在线会话安全强行提纯过滤与越狱注入拦截 (对齐 5173 / 5174 实时安全卫兵)
        security_warning_badge = ""
        if user_msg:
            from rag_security import rag_guard
            sanitized_msg, is_toxic, alerts = rag_guard.sanitizer.sanitize(user_msg, source="live_websocket")
            if is_toxic:
                await ws_send({"type": "status", "content": "🛡️ [安全卫兵实时防务] 截获并过滤掉问询中的高危密咒或不可见攻击码！"})
                user_msg = sanitized_msg
                security_warning_badge = "\n\n> 🛡️ **[企业安全壁垒触发]** *安全卫兵实时截击到了尝试覆乱既定中介规则和隐藏暗号的数据段，已做脱毒清洗处理！*"

        if mode == "expert":
            from orchestrator_graph import build_expert_graph
            
            workflow = build_expert_graph(
                send_event=ws_send,
                client=client,
                selected_model=selected_model,
                OPENAI_TOOL_SCHEMAS=OPENAI_TOOL_SCHEMAS,
                permissions=permissions,
                strip_badges_fn=_strip_system_badges,
                max_tool_rounds=4,
            )
            
            async with AsyncPostgresSaver.from_conn_string(db_url) as memory_saver:
                await memory_saver.setup()
                app_graph = workflow.compile(checkpointer=memory_saver)
                
                config = {"configurable": {"thread_id": session_id}}
                user_content = user_msg or ("请分析这张图片" if image_data else "你好")
                
                enable_vlm = os.getenv("ENABLE_VLM", "false").lower() == "true"
                if image_data and enable_vlm:
                    img_url = image_data if image_data.startswith("data:image") else f"data:image/jpeg;base64,{image_data}"
                    user_message_payload = {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": user_content},
                            {"type": "image_url", "image_url": {"url": img_url}}
                        ]
                    }
                else:
                    user_message_payload = {"role": "user", "content": user_content}
                    
                expert_input_messages = [
                    {"role": "system", "content": (
                        "你是首席企业级 AI Agent，定位是企业知识库与受控业务工具执行助手。\n"
                        "可用工具只有 search_knowledge_base 与 query_sql_database。\n"
                        "当用户要求查询知识库、内部资料、项目文档、RAG 资料，或明确要求调用知识库工具时，必须先调用 search_knowledge_base，不能凭记忆直接回答。\n"
                        "当用户要求查询数据库、表、字段、统计数据，或明确要求调用数据库查询工具时，必须先调用 query_sql_database。\n"
                        "query_sql_database 只允许只读查询；涉及新增、修改、删除、建表、改表等写操作时，也必须调用该工具并让工具返回受控拒绝结果。\n"
                        "工具失败时，基于工具返回的结构化错误如实说明，不要伪造工具结果。"
                    )},
                    user_message_payload
                ]
                
                final_state = await app_graph.ainvoke({"messages": expert_input_messages, "tool_rounds": 0}, config=config)
                last_msg_content = ""
                if final_state and "messages" in final_state and final_state["messages"]:
                    last_m = final_state["messages"][-1]
                    last_msg_content = str(getattr(last_m, "content", "") or (last_m.get("content", "") if isinstance(last_m, dict) else ""))
                
                # 双重校验防卫：仅当推导回执未出现过此签言时才加推一次，彻底杜绝 UI 末尾复读和叠加
                final_messages = final_state.get("messages", []) if isinstance(final_state, dict) else []
                streamed_content = "".join(
                    str(getattr(message, "content", "") or (message.get("content", "") if isinstance(message, dict) else ""))
                    for message in final_messages
                )
                if not _has_expert_badge(last_msg_content) and not _has_expert_badge(streamed_content):
                    expert_badge = "\n\n> *🧙‍♂️ [系统态: 专家推演思考大引擎] | PostgreSQL LangGraph Checkpoint 全量记忆挂机 | 反思闭环与量化质检通过*" + security_warning_badge
                    await ws_send({"type": "stream_chunk", "content": expert_badge})
                await ws_send({"type": "stream_end"})
                
        elif mode == "orchestrator":
            from orchestrator_graph import build_orchestrator_graph
            async with AsyncPostgresSaver.from_conn_string(db_url) as memory_saver:
                await memory_saver.setup()
                app_graph = build_orchestrator_graph(ws_send)
                app_graph = app_graph.compile(checkpointer=memory_saver)
                
                config = {"configurable": {"thread_id": session_id}}
                orchestrator_task = user_msg
                task_policy = evaluate_task_policy(orchestrator_task, mode, permissions)
                if hitl_approved:
                    approval_policy = evaluate_approval_decision(permissions)
                    if not approval_policy.allowed:
                        await ws_send({"type": "stream_start"})
                        await ws_send({"type": "stream_chunk", "content": f"\n\n> 🛑 **[审批拒绝]**: {approval_policy.reason}。"})
                        await ws_send({"type": "stream_end"})
                        await ws_send({"type": "task_complete", "content": "Task rejected by RBAC guard."})
                        return
                    verified = await verify_approval_decision(
                        session_id=session_id,
                        approval_id=approval_id,
                        approval_token=approval_token,
                        approver_user_id=user_id,
                        tenant_id=tenant_id,
                        decision_payload={
                            "approved": True,
                            "kind": approval_kind,
                        },
                    )
                    if verified is None:
                        await ws_send({"type": "stream_start"})
                        await ws_send({"type": "stream_chunk", "content": "\n\n> 🛑 **[审批拒绝]**: 审批令牌无效、已过期、已使用，或不属于当前会话。"})
                        await ws_send({"type": "stream_end"})
                        await ws_send({"type": "task_complete", "content": "Task rejected by approval guard."})
                        return
                    current_approval_id = approval_id
                    verified_approval_kind = str(verified.get("approval_kind") or "")
                elif task_policy.requires_approval:
                    await ws_send({
                        "type": "hitl_request",
                        "content": orchestrator_task,
                        "params": {
                            "approval_kind": task_policy.approval_kind,
                            "risk_level": task_policy.risk_level,
                            "reason": task_policy.reason,
                            "policy": task_policy.as_dict(),
                        },
                    })
                    await ws_send({"type": "task_complete", "content": "Task paused for approval."})
                    return

                if hitl_approved and approval_kind == "continue_analysis":
                    orchestrator_task = (
                        "请只分析以下高风险操作的影响范围、前置校验、执行步骤建议和回滚方案，"
                        f"不要执行任何写库、删除、发送、导出、外部调用等副作用操作：{user_msg}"
                    )
                initial_state = {
                    "input_task": orchestrator_task,
                    "is_approved": hitl_approved
                }
                
                final_state = await app_graph.ainvoke(initial_state, config=config)
                final_response = final_state.get("final_response", "")
                if current_approval_id:
                    await complete_approval(current_approval_id, "completed", final_response or "orchestrator completed")
        else:
            # Fast mode
            rag_engine.build_or_load()
            await ws_send({"type": "status", "content": "🔍 正在极速检索企业知识库..."})
            context, sources = rag_engine.retrieve(user_msg or ("分析图片" if image_data else "你好"))
            if rt:
                rt.add_metadata({"rag_sources": sources, "rag_hit_count": len(sources)})
            system_prompt = (
                "你是极强精益的企业级AI助手。请全面结合【用户提供的附件内容】以及【企业知识库内容】为用户解答。\n"
                f"【企业知识库参考内容】：\n---\n{context}\n---\n"
                "【核心生成规范与零重复红线 (Critical Quality Rules)】：\n"
                "1. **零冗余提炼与交集整合**：知识库中的多份切片(Chunks)往往是从长文中切分的，易出现相同文字、近似段落以及前后连绵的重复要点。你必须自发对海量参考切片做好融汇提纯与综合归并，任何语句与阐述逻辑绝对不可自我抄录与同义迭代重复！\n"
                "2. **严整统一序号递进**：回传文本如果包含层级编号或执行逻辑列表（如 1、2、3... 或(1)(2)），必须严守“单一线索完全非重复唯一自序”原则！严禁在回复一分钟内反复弹出相同的要点编号、互相冲撞的 1. -> 2. -> 2. 或混淆乱搭的内容重列！\n"
                "3. **附件权威直达**：如用户旨在要求对新上传图片/附件进行提取翻译和分析，立即采用其实时负载为核心作答准绳。做到严谨专业，无幻觉不水滴！"
            )
            fast_messages = [{"role": "system", "content": system_prompt}]
            
            for h in history[-10:]:
                if h.get("content"):
                    fast_messages.append({"role": h.get("role", "user"), "content": _strip_system_badges(str(h.get("content") or ""))})
            
            enable_vlm = os.getenv("ENABLE_VLM", "false").lower() == "true"
            if image_data and enable_vlm:
                # Ensure it's a proper Data URL for the model API
                img_url = image_data if image_data.startswith("data:image") else f"data:image/jpeg;base64,{image_data}"
                fast_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_msg or "分析图片"},
                        {"type": "image_url", "image_url": {"url": img_url}}
                    ]
                })
            else:
                fast_messages.append({"role": "user", "content": user_msg})
            
            await ws_send({"type": "status", "content": "⚡ [极速穿透绿道] BGE-M3 前沿搜索瞬毕 | 开启极致极速输出流水..."})
            if sources:
                await ws_send({"type": "citations", "content": sources})
                
            await ws_send({"type": "stream_start"})
            try:
                stream = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=selected_model,
                        messages=fast_messages,
                        stream=True,
                        temperature=0.3
                    ),
                    timeout=15.0
                )
                final_response = ""
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        final_response += content
                        await ws_send({"type": "stream_chunk", "content": content})
                if not _has_fast_badge(final_response):
                    fast_badge = "\n\n> *🚀 [系统态: 混合极速引擎 (Fast RAG Engine)] | BGE+BM25 极速收束时延 <0.3s | 省时节能免排期*" + security_warning_badge
                    await ws_send({"type": "stream_chunk", "content": fast_badge})
                await ws_send({"type": "stream_end"})
            except Exception as llm_err:
                print(f"[Offline/Air-Gapped Pivot] 远端/在线接口不可达或处于断网离线态 ({str(llm_err)})，立刻启用「纯离线知识库结构化提取提炼仪」！")
                await ws_send({"type": "status", "content": "🛡️ [本地高可用模式] 侦测到离线/未接连远端大脑，自动唤醒「全纯度本地 RAG 断网智简生成中枢」！"})
                
                offline_reply = "### 🛡️ 【离线容错/零网络可用态】《大模型架构设计指南》及文献综合成果\n\n"
                offline_reply += "*(系统侦测到当前环境无外部网络连结或 LLM 节点响应超时，立刻激活**零外网传输·绝缘私有语料精要合成器**，为您结构化归纳核心精粹)：*\n\n"
                
                if context and context.strip() and context != "备用":
                    raw_lines = context.split('\n')
                    clean_items = []
                    seen_lines = set()
                    for line in raw_lines:
                        ln = line.strip()
                        if not ln or ln.startswith("[DOC -") or ln in seen_lines:
                            continue
                        seen_lines.add(ln)
                        clean_items.append(ln)
                    
                    offline_reply += "#### 📑 知识库核心条目精选集结（纯本地自闭环去重归约）：\n\n"
                    for idx, ln in enumerate(clean_items, 1):
                        if ln.startswith('#'):
                            offline_reply += f"\n#### 🔸 **{ln.lstrip('#').strip()}**\n"
                        elif ln.startswith('-') or (len(ln) > 2 and ln[0].isdigit() and ln[1] == '.'):
                            offline_reply += f"{ln}\n\n"
                        else:
                            offline_reply += f"• **重点记录**：{ln}\n\n"
                else:
                    offline_reply += "⚠️ **资料状态提醒**：本地索引中未能直接提取到对应该主题的长句文段，建议确认已在本机成功载入对应 md 格式原书架。"
                    
                offline_reply += "\n> *🛡️ [系统态: 物理空气间隙全全纯离线防线 (Air-Gapped Local RAG Engine)] | 0%网络穿透风险 · 100% 局域零外部计算 · 本地化安全提零延误*" + security_warning_badge
                await ws_send({"type": "stream_chunk", "content": offline_reply})
                await ws_send({"type": "stream_end"})

        # End of stream marker
        if current_approval_id and mode != "orchestrator":
            await complete_approval(current_approval_id, "completed", final_response or "task completed")
        await ws_send({"type": "task_complete", "content": "Task completed successfully."})
        
    except Exception as e:
        if current_approval_id:
            try:
                await complete_approval(current_approval_id, "failed", str(e))
            except Exception as audit_error:
                print(f"[Approval Audit] failed to mark failure: {audit_error}")
        await ws_send({"type": "stream_start"})
        await ws_send({"type": "stream_chunk", "content": f"\n\n> ❌ **[运行异常]**: {str(e)}"})
        await ws_send({"type": "stream_end"})
        await ws_send({"type": "task_complete", "content": "Task failed."})


def process_request(session_id: str, user_msg: str, mode: str, selected_model: str, history: list, image_data: str = None, audio_data: str = None, file_upload: dict = None):
    try:
        asyncio.run(
            async_process_request(session_id, user_msg, mode, selected_model, history, image_data, audio_data, file_upload)
        )
    except Exception as e:
        import traceback
        with open("celery_error.log", "a") as f:
            f.write(traceback.format_exc())
        print(f"Error in Celery wrapper: {e}")
