"""
企业级分层 Prompt 框架设计
============================
架构分为四层（从底层到顶层）：
  Layer 1: System Prompt   - 角色身份与全局约束（几乎不变）
  Layer 2: 示例库           - Few-Shot 样例池（定期人工维护）
  Layer 3: 任务 Prompt     - 本次任务的具体指令与格式要求（按场景切换）
  Layer 4: 参数模板         - 运行时动态注入的业务变量（每次请求都不同）

设计原则：
  - 稳定层放上面，变化层放下面，避免底层稳定的内容被业务噪音污染
  - 每层独立管理、独立版本控制，出问题快速定位是哪一层的 Prompt 发生了漂移
  - 示例库与任务 Prompt 解耦，同一批示例可被多个任务复用
"""

from dataclasses import dataclass, field
from typing import Optional
from string import Template
from enum import Enum
import json


# ============================================================
# Layer 1: System Prompt 层（角色身份 + 全局约束）
# ============================================================
# 意义：给大模型定义一个稳定的"人格"和不可违背的底线约束。
# 这一层在整个产品生命周期内几乎不会改动，类比软件的"宪法"。
# 写好这一层，大模型在任何场景下都不会"犯法"。

SYSTEM_PROMPTS = {
    "legal_assistant": """
你是一名资深法律助手，专注于中国劳动法和合同法领域。

【角色约束 - 不可违背】
1. 你只能基于用户提供的文件和知识库内容进行分析，严禁编造法条或案例。
2. 如果知识库内容不足以回答，必须明确说明："根据现有资料无法确定，建议咨询专业律师。"
3. 你的回答不构成正式法律意见，末尾必须附带免责声明。
4. 禁止在未明确说明的情况下引用1年以上的旧法规，法律会更新。

【输出风格】
- 结构清晰，使用编号列表
- 关键法条必须注明出处（如《劳动合同法》第X条）
- 语言专业但通俗易懂
""",

    "customer_service": """
你是「星辰科技」的资深客户服务代表，负责处理售后问题、产品咨询和投诉。

【角色约束 - 不可违背】
1. 始终保持友善、耐心、专业的态度，不可与用户发生争执。
2. 在没有明确的知识库支撑时，不可承诺具体的赔偿金额或时间节点。
3. 用户情绪激动时，优先共情安抚，再处理问题。
4. 涉及退款金额超过 1000 元的诉求，必须引导升级至人工专席。

【输出风格】
- 开头使用问候语，结尾使用感谢语
- 语言亲切，减少专业术语，使用"您"而非"你"
""",
}


# ============================================================
# Layer 2: 示例库层（Few-Shot 样例池）
# ============================================================
# 意义：给大模型演示"正确答案长什么样"。
# 与任务 Prompt 解耦，一套样例可以被多个不同的任务场景复用。
# 关键设计：样例必须按难度、场景类型分组，由人工定期审核维护。

@dataclass
class FewShotExample:
    """结构化的 Few-Shot 样例，便于管理和复用"""
    scenario: str         # 适用场景 tag
    difficulty: str       # easy / medium / hard
    user_input: str
    expected_output: str
    annotation: str = ""  # 人工注释：这个样例的示范点是什么


# 法律助手示例库
LEGAL_EXAMPLES = [
    FewShotExample(
        scenario="severance_pay",
        difficulty="easy",
        user_input="我被公司辞退了，工作了3年，应该赔偿多少？",
        expected_output=(
            "根据《劳动合同法》第47条，经济补偿按工作年限计算，每满1年支付1个月工资。\n"
            "您的情况：工作年限3年 × 月工资 = 3个月工资。\n\n"
            "⚠️ 免责声明：以上分析仅供参考，不构成正式法律意见。"
        ),
        annotation="示范：精确引用法条编号 + 给出具体计算公式 + 末尾必须有免责声明"
    ),
    FewShotExample(
        scenario="unknown_question",
        difficulty="easy",
        user_input="明朝的劳动法是怎么规定的？",
        expected_output=(
            "抱歉，您的问题超出了本系统的知识库范围（中国现行劳动法律体系）。\n"
            "根据现有资料无法确定，建议咨询专业律师或相关历史学者。"
        ),
        annotation="示范：知识库无法覆盖时，必须主动拒绝而非编造答案"
    ),
]

# 客服示例库
CUSTOMER_SERVICE_EXAMPLES = [
    FewShotExample(
        scenario="product_complaint",
        difficulty="medium",
        user_input="你们的产品用了才两周就坏了，太差劲了！",
        expected_output=(
            "您好！非常抱歉给您带来了不好的体验，我完全理解您现在的心情 😔\n\n"
            "请您放心，我会帮您全力处理这个问题。为了能更快为您解决，"
            "能否告诉我：\n1. 具体是哪个功能出现了问题？\n2. 您的订单号是多少？\n\n"
            "感谢您的耐心，我们一定会给您一个满意的答复！"
        ),
        annotation="示范：先共情安抚（情绪激动场景），再引导提供信息，结尾感谢"
    ),
]

# 示例库索引（按场景 tag 快速检索对应样例）
EXAMPLE_LIBRARY = {
    "legal_assistant": LEGAL_EXAMPLES,
    "customer_service": CUSTOMER_SERVICE_EXAMPLES,
}


# ============================================================
# Layer 3: 任务 Prompt 层（本次任务的具体指令）
# ============================================================
# 意义：告诉大模型"这次具体要做什么事"、"输出格式要求"。
# 这一层按业务场景进行切换，不同任务注入不同的任务 Prompt。
# 注意：此层不放业务数据（那是 Layer 4 的事情）

TASK_PROMPTS = {
    # 任务：根据合同文件分析违约风险
    "contract_risk_analysis": """
【当前任务：合同违约风险分析】

你需要分析用户提供的合同文件，识别出潜在的法律风险点。

输出格式必须严格按照以下 JSON 结构（不允许有额外说明文字）：
```json
{
  "risk_level": "高/中/低",
  "risk_points": [
    {
      "clause": "风险条款原文",
      "issue": "风险描述",
      "suggestion": "修改建议",
      "law_reference": "相关法条"
    }
  ],
  "overall_suggestion": "总体建议"
}
```
""",

    # 任务：退款处理
    "refund_processing": """
【当前任务：退款申请处理】

你需要判断用户的退款申请是否符合公司退款政策，并给出处理方案。

处理规则（严格按此优先级执行）：
1. 7天无理由退款 → 直接同意，引导走退款流程
2. 7-30天质量问题 → 要求提供证据（照片/视频），上报审核
3. 30天以上 → 告知超出退款窗口期，提供维修方案

输出必须包含以下三个部分：
- 【判断结果】：符合/不符合/需要审核
- 【处理方案】：具体操作步骤
- 【话术建议】：给客服人员的推荐回复话术
""",
}


# ============================================================
# Layer 4: 参数模板层（运行时动态注入的业务变量）
# ============================================================
# 意义：将静态 Prompt 和动态业务数据完全分离。
# 类比：HTML 模板和数据库数据分离。Prompt 是模板，业务数据是数据库。
# 核心好处：Prompt 模板可以复用，测试时可以固定模板、只换数据。

@dataclass
class PromptContext:
    """运行时参数：每次请求都不同的业务变量"""
    user_query: str                          # 用户原始问题
    retrieved_docs: list[str] = field(default_factory=list)   # RAG 检索出的文档片段
    user_profile: dict = field(default_factory=dict)          # 用户画像（VIP等级、历史记录等）
    current_date: str = ""                   # 当前日期（让模型知道时间背景）
    business_metadata: dict = field(default_factory=dict)     # 业务元数据（订单号、产品信息等）


PARAM_TEMPLATE = Template("""
【参考知识库文档】
$retrieved_docs

【用户信息】
- 用户等级: $user_level
- 提交时间: $current_date

【用户问题】
$user_query
""")


# ============================================================
# 核心组装器：将四层 Prompt 合并为最终发给大模型的消息列表
# ============================================================

class PromptFramework:
    """
    分层 Prompt 框架的核心组装器
    对外提供统一的 build() 接口，内部屏蔽四层的组装细节
    """

    def build(
        self,
        role: str,                     # 角色 key，决定用哪个 System Prompt
        task: str,                     # 任务 key，决定用哪个 Task Prompt
        context: PromptContext,        # 运行时业务参数
        max_examples: int = 2,        # 最多注入几条 Few-Shot 样例
    ) -> list[dict]:
        """
        组装并返回符合 OpenAI Chat API 格式的消息列表
        [{role: system, content: ...}, {role: user, content: ...}, ...]
        """
        messages = []

        # ── Step 1: 注入 System Prompt (Layer 1) ──────────────
        system_content = SYSTEM_PROMPTS.get(role, "你是一个有用的助手。")

        # ── Step 2: 将任务 Prompt 拼接到 System 中 (Layer 3) ──
        task_content = TASK_PROMPTS.get(task, "")
        if task_content:
            system_content += f"\n\n{task_content}"

        messages.append({"role": "system", "content": system_content.strip()})

        # ── Step 3: 注入 Few-Shot 样例 (Layer 2) ──────────────
        examples = EXAMPLE_LIBRARY.get(role, [])[:max_examples]
        for example in examples:
            messages.append({"role": "user", "content": example.user_input})
            messages.append({"role": "assistant", "content": example.expected_output})

        # ── Step 4: 注入运行时参数模板 (Layer 4) ─────────────
        docs_text = "\n---\n".join(context.retrieved_docs) if context.retrieved_docs else "（无相关文档）"
        user_message = PARAM_TEMPLATE.substitute(
            retrieved_docs=docs_text,
            user_level=context.user_profile.get("level", "普通用户"),
            current_date=context.current_date or "未知",
            user_query=context.user_query,
        )
        messages.append({"role": "user", "content": user_message.strip()})

        return messages

    def preview(self, messages: list[dict]):
        """打印完整的 Prompt 结构，用于调试和审核"""
        print("\n" + "=" * 65)
        print("📋 完整 Prompt 预览（发送给大模型前的最终形态）")
        print("=" * 65)
        for i, msg in enumerate(messages):
            role_icon = {"system": "🔧 SYSTEM", "user": "👤 USER", "assistant": "🤖 ASSISTANT"}.get(msg["role"], msg["role"])
            print(f"\n── [{i+1}] {role_icon} {'─'*40}")
            print(msg["content"])
        print("\n" + "=" * 65)
        print(f"📊 统计: 共 {len(messages)} 条消息 | "
              f"总字符数: {sum(len(m['content']) for m in messages)}")


# ============================================================
# 演示：组装一次完整的法律助手请求
# ============================================================
if __name__ == "__main__":
    framework = PromptFramework()

    # 模拟一次 RAG 请求的运行时上下文
    context = PromptContext(
        user_query="我被公司辞退，工作了5年，他们只给了我2个月工资，合理吗？",
        retrieved_docs=[
            "《劳动合同法》第47条：经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。",
            "《劳动合同法》第48条：用人单位违反本法规定解除或者终止劳动合同，劳动者要求继续履行劳动合同的，用人单位应当继续履行。"
        ],
        user_profile={"level": "VIP用户", "case_id": "CASE-20260708"},
        current_date="2026年7月8日",
        business_metadata={"department": "法律咨询"},
    )

    # 组装四层 Prompt
    messages = framework.build(
        role="legal_assistant",
        task="contract_risk_analysis",
        context=context,
        max_examples=1,   # 只注入1条示例，节省 Token
    )

    # 预览最终发给大模型的完整 Prompt
    framework.preview(messages)

    print("\n💡 提示: 将上面的 messages 列表直接传入 openai.chat.completions.create(messages=...) 即可")
    print("   这套框架与 LangChain / DSPy / 原生 OpenAI SDK 完全兼容\n")
