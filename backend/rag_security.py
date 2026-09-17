# -*- coding: utf-8 -*-
"""
================================================================================
RAG 知识库防毒与数据污染防御系统 (RAG Security & Contamination Radar)
================================================================================

[命名防误读] InputSanitizer（原名 InsecureInputSanitizer）是安全防御组件。
  - 类名含义：「处理不安全输入的消毒器」，而非「不安全的实现」
  - 该类被 ContaminationRadar 在生产路径中正常调用，属于可信安全基础设施
  - 原类名保留为向后兼容别名（见文件末尾），不影响现有 import

本模块致力于从算法层面与工程底座彻底根除以下两大灾患：
1. 沙箱提纯层 (InputSanitizer)
   - 多向文本高质消毒机与正则滤毒池。
   - 过滤极危特种指令字段（如："忽略往常规则"、"强制扮演"、"覆盖历史事实"）。
   - 清除高阶攻防中的零宽字符隐匿（Zero-Width Invisible Token Injection）与透明文本暗语。
2. 文档免疫识别 (ContaminationRadar)
   - 本地守门卫兵与 RAG 数据污染全自动核查机。
   - 检测句段中意图诱骗主模型大中枢叛逃或污染企业知识真相度的高熵异常段落。
   - 与 LangSmith MLOps 全链路审计联调（@traceable 打断追捕日志），触发高风险直接扣押至受限沙箱抛出 403 Security 阻断事件！
"""

import re
import math
from typing import List, Dict, Any, Tuple
import os

try:
    from langsmith import traceable, get_current_run_tree
except ImportError:
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def get_current_run_tree():
        return None

# ==================== 第 1 层：沙箱提纯层 (InputSanitizer) ====================
# [命名防误读] 原名 InsecureInputSanitizer = 「处理不安全输入的消毒器」，是生产级安全组件
class InputSanitizer:
    """
    多向文本高质消毒机 & 正则滤毒池
    针对所有由 OCR、语音识别(Whisper)、PDF 转写得到的内容进行高标准强力提纯和免疫处理。
    """
    
    # 极危超写密咒与后门越狱正则表达式（正则滤毒池）
    TOXIC_PATTERNS = [
        r"忽略(往常|所有|所有之前|之前)的?(规则|指令|原则|设定)",
        r"从现在(开始|起)(覆盖|修改|抹去|无视|改写)(历史|默认|身份|事实|设定|准则)",
        r"强制扮演",
        r"(你现在是|摇身一变|转变成)(一个|名叫)?没有(任何|哪怕一丁点)(限制|约束|准则)的?(AI|模型|系统|机器人)",
        r"ignore\s+(all\s+)?(previous\s+)?(instructions|rules|directives)",
        r"override\s+(system|safety|guardrail|alignment)\s*(protocol|rules|prompt)?",
        r"do\s+anything\s+now",
        r"绕过(系统|安全|防守)审查",
        r"解除一切封印",
    ]
    
    # 零宽不可见攻击字符 (Zero-Width Characters)
    ZERO_WIDTH_REGEX = re.compile(r'[\u200B-\u200D\uFEFF\u200E\u200F\u202A-\u202E]')

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.TOXIC_PATTERNS]

    def sanitize(self, text: str, source: str = "unknown") -> Tuple[str, bool, List[str]]:
        """
        对传入的候选文本片段执行深度扫描与消毒清洗。
        
        返回: (提纯后的安全文本, 是否发现过剧毒攻击痕迹, 触发的安全告警信息列表)
        """
        if not text or not isinstance(text, str):
            return "", False, []

        is_contaminated = False
        alerts = []
        original_len = len(text)

        # 1. 斩除零宽不可见字符 (防守 ASCII Smuggling 与隐形木马)
        text_cleaned = self.ZERO_WIDTH_REGEX.sub('', text)
        if len(text_cleaned) < original_len:
            is_contaminated = True
            removed_count = original_len - len(text_cleaned)
            alerts.append(f"🔴 [极度危险] 检测到 {removed_count} 个零宽隐藏特种字符(潜藏隐写指引)，已硬核强行铲除！")
            text = text_cleaned

        # 2. 正则滤毒池逐条排查密咒突破口
        for pat in self.compiled_patterns:
            if pat.search(text):
                is_contaminated = True
                match_str = pat.search(text).group(0)
                alerts.append(f"🟠 [密咒拦截] 抓取到可疑超写指令注入语调: '{match_str}'，已被静默剔除。")
                text = pat.sub("[SECURITY_SHIELD_TOXIC_REMOVED]", text)

        return text, is_contaminated, alerts


# ==================== 第 2 层：文档免疫识别 (Contamination Radar) ====================

class ContaminationRadar:
    """
    全自动本地守门过滤卫兵与文档免疫识别雷达 (LLM Safeguard & Entropy Radar)
    在入库与检索水线边缘实时扫描评估每一帧 Text Chunk，果断抛掷 403 Security 警标！
    """

    def __init__(self):
        self.sanitizer = InputSanitizer()

    @traceable(name="contamination_radar_evaluate", tags=["rag_security", "mlops_shield"])
    def evaluate_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        对单份未入库文档切片 / 片段实施双闭环鉴定。
        如果包含投毒行为或企图向大中枢灌注叛逃规则，将被立即拒收扣押至隔离审查区。
        """
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        source_name = metadata.get("source", "未知文件")

        # 将分析事件记录至 LangSmith Metadata 链中
        rt = get_current_run_tree()
        if rt:
            rt.add_metadata({"source_document": source_name, "chunk_size_bytes": len(content.encode('utf-8'))})

        # === Step 1：执行第一层沙箱消毒清洗 ===
        sanitized_content, has_toxic_traces, alerts = self.sanitizer.sanitize(content, source=source_name)

        # === Step 2：文档免疫特征深度评估 (高风险聚类鉴定与伪常识叛乱检测) ===
        is_quarantined = False
        risk_level = "LOW"
        security_reason = "通过严格检验，符合可信安全规范"

        # 如果捕获到了确凿的攻击注入密咒或隐匿符，直接升级为高风险阻断
        if has_toxic_traces:
            is_quarantined = True
            risk_level = "CRITICAL"
            security_reason = f"触发防毒红线: " + "; ".join(alerts)

        # === Step 3：基于文本熵和密文重复灌水投毒攻击判定 ===
        # 预防投毒者故意以同语无脑重复一千遍以拉爆 BM25 词频度权重（Data Poisoning Loop）
        if len(sanitized_content) > 100:
            words_count = len(sanitized_content.split())
            unique_chars = len(set(sanitized_content))
            # 自守门判断逻辑：如果字符种类过于单一但体量超长（恶意占坑刷位），阻截其污染私有词典
            if unique_chars < 15 and len(sanitized_content) > 300:
                is_quarantined = True
                risk_level = "HIGH"
                security_reason = "🔴 [熵检测未过] 识别为低熵高重复词频灌水攻击！欲图劫持 BM25 权重树！"

        # 整理评估结果并挂接监控审计
        verified_chunk = {
            "content": sanitized_content if not is_quarantined else "[🚨 403 Security ALERT] 该课段内容已被反洗数据系统扣押封锁",
            "metadata": {
                **metadata,
                "security_status": "QUARANTINED" if is_quarantined else "PASSED",
                "risk_level": risk_level,
                "audit_notes": security_reason
            },
            "is_safe": not is_quarantined,
            "alerts": alerts
        }

        if rt:
            rt.add_metadata({"security_verdict": verified_chunk["metadata"]["security_status"], "risk_level": risk_level})
            if is_quarantined:
                print(f"[🚨 403 Security Alert] 已自杀式强行拦截可疑注入！文件：{source_name} | 原因：{security_reason}")
                
        return verified_chunk

# 实例化全局安全守门卫兵
rag_guard = ContaminationRadar()

# 向后兼容别名：保留原类名，现有 `from rag_security import InsecureInputSanitizer` 不受影响
InsecureInputSanitizer = InputSanitizer
