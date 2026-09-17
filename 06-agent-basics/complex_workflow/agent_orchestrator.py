"""
agent_orchestrator.py
=====================
Plan-and-Execute Agent 完整实现（生产级架构）

架构流程图：
    User
      |
    Agent (StateGraph)
      |
    ┌─────────────────────┐
    |  LLM  Memory  Tools  |
    └─────────────────────┘
      |
    Planning → Execution (内嵌 ReAct) → Replanning → END

核心组件：
  - Planning    : 全局拆解任务，不碰工具
  - Execution   : 内嵌 ReAct 循环，结合 Tools 死磕单一子任务
  - Replanning  : 校验目标是否达成，未达成则生成补救计划
  - Memory      : SqliteSaver 持久化，支持跨进程会话恢复
  - Tools       : 关键词路由动态挂载，防止 LLM 工具幻觉

使用方式：
    python agent_orchestrator.py
"""

import os
import json
import logging
from typing import List, Tuple, Optional

from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
# LangGraph v1.0 已将 create_react_agent 迁移至 langchain.agents，
# 此处暂保留 prebuilt 导入（仍可用），待项目统一升级后迁移
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# ==========================================
# 日志配置
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ==========================================
# 全局防护常量
# ==========================================
MAX_ITERATIONS: int = 5        # 最大全局迭代次数（防止 Replanner 无限循环）
MAX_REPLAN_COUNT: int = 2      # Replanner 最多重新规划次数


# ==========================================
# 1. 定义全局状态 (Memory — 短期，运行时)
# ==========================================
class AgentState(TypedDict):
    task: str                           # 用户原始复杂大目标
    plan: List[str]                     # 待执行的子任务计划列表（动态更新）
    past_steps: List[Tuple[str, str]]   # 执行足迹：记录 (子任务名, 执行结果)
    final_answer: str                   # 最终交付给用户的答案
    iterations: int                     # 全局迭代计数（防无限循环）
    replan_count: int                   # Replanner 重规划次数计数


# ==========================================
# 2. 初始化 LLM
# ==========================================
model = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.1,
    max_retries=3,
)


# ==========================================
# 3. 定义工具 (Tools)
#    三类工具：搜索 / 内容生成 / 天气查询（来自 MCP）
# ==========================================

@tool
def simulate_web_search(query: str) -> str:
    """
    模拟网络搜索引擎，根据查询关键词返回相关背景资料。
    适用于：需要收集外部信息、市场调研、事实查询等任务。
    """
    logger.info("[Tool:simulate_web_search] query=%s", query)
    # 在真实生产中，这里调用 Google/Bing/Tavily API
    # 此处用 LLM 模拟以避免真实网络依赖，降低学习门槛
    try:
        prompt = (
            f"你是一个搜索引擎。请根据以下查询词，返回 3~5 条简洁的背景资料摘要（每条不超过50字）：\n{query}"
        )
        result = model.invoke([HumanMessage(content=prompt)]).content
        return f"[搜索结果]\n{result}"
    except Exception as e:
        logger.error("[Tool:simulate_web_search] 调用失败: %s", e)
        return f"[搜索失败] 无法获取关于 '{query}' 的信息，错误: {e}"


@tool
def generate_section_content(section_title: str, background_info: str) -> str:
    """
    根据章节标题和背景资料，调用 LLM 生成该章节的详细内容。
    适用于：报告撰写、文档生成、章节内容填充等任务。
    """
    logger.info("[Tool:generate_section_content] section_title=%s", section_title)
    try:
        prompt = (
            f"你是一名专业报告撰写人。请根据以下背景资料，"
            f"为章节「{section_title}」撰写200~300字的正文内容。\n\n"
            f"背景资料：{background_info}"
        )
        result = model.invoke([HumanMessage(content=prompt)]).content
        return f"[章节内容 — {section_title}]\n{result}"
    except Exception as e:
        logger.error("[Tool:generate_section_content] 调用失败: %s", e)
        return f"[内容生成失败] 章节 '{section_title}' 生成出错，错误: {e}"


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的天气信息。
    适用于：需要天气数据的报告或计划任务。
    """
    logger.info("[Tool:get_weather] city=%s", city)
    # 模拟天气数据，真实场景对接 MCP 天气服务
    return f"[天气查询] {city}：晴，温度 28℃，适宜户外活动。"


# ==========================================
# 4. 动态工具路由（关键词匹配策略）
#    按任务内容动态分配工具包，避免 LLM 工具幻觉
# ==========================================
SEARCH_KEYWORDS: List[str] = ["搜索", "查询", "收集", "调研", "检索", "了解", "找", "获取"]
WRITE_KEYWORDS: List[str] = ["撰写", "生成", "写", "输出", "整合", "汇总", "报告", "内容"]
WEATHER_KEYWORDS: List[str] = ["天气", "气温", "weather", "气候"]

ALL_TOOLS = {
    "search": [simulate_web_search],
    "write": [generate_section_content],
    "weather": [get_weather],
    "default": [simulate_web_search, generate_section_content],
}


def select_tools_for_task(task: str) -> list:
    """
    根据任务关键词动态选择工具集合。
    简单可靠的关键词匹配策略，防止一次性给 LLM 过多工具。
    """
    task_lower = task.lower()

    if any(kw in task_lower for kw in WEATHER_KEYWORDS):
        logger.info("[ToolRouter] 路由到: weather 工具")
        return ALL_TOOLS["weather"]

    if any(kw in task_lower for kw in WRITE_KEYWORDS) and not any(kw in task_lower for kw in SEARCH_KEYWORDS):
        logger.info("[ToolRouter] 路由到: write 工具")
        return ALL_TOOLS["write"]

    if any(kw in task_lower for kw in SEARCH_KEYWORDS) and not any(kw in task_lower for kw in WRITE_KEYWORDS):
        logger.info("[ToolRouter] 路由到: search 工具")
        return ALL_TOOLS["search"]

    # 默认：搜索 + 写作均可用（最通用的任务）
    logger.info("[ToolRouter] 路由到: default (search + write) 工具")
    return ALL_TOOLS["default"]


# ==========================================
# 5. 节点 1：Planner（规划器）
#    职责：宏观拆解任务，不调用任何工具
# ==========================================
PLANNER_SYSTEM_PROMPT = """你是一个资深的 AI 项目经理。
你的职责是将用户的复杂目标，拆解为 3~5 个可执行的具体子任务，每个子任务必须能被一个执行者独立完成。

规则：
1. 严格输出 JSON 格式的字符串列表，不要有任何额外解释
2. 每个子任务必须具体、可操作（如"搜索 XX 背景资料"而非"调研"）
3. 子任务数量控制在 3~5 个之间

输出示例：["搜索旧金山AI峰会的历史案例", "生成峰会日程安排章节", "生成预算表章节", "汇总最终报告"]"""


def planner_node(state: AgentState) -> dict:
    """
    规划器节点：接收用户任务，输出 plan 子任务队列。
    不调用任何工具，只使用 LLM 进行宏观决策。
    """
    logger.info("\n🧠 [Planner] 开始拆解任务...")
    task = state["task"]

    try:
        response = model.invoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"请拆解以下任务：{task}"),
        ])
        content = response.content.strip().replace("```json", "").replace("```", "").strip()
        plan: List[str] = json.loads(content)

        if not isinstance(plan, list) or len(plan) == 0:
            raise ValueError("规划器输出格式不正确")

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("[Planner] JSON 解析失败，启用兜底计划: %s", e)
        plan = ["收集相关背景资料", "撰写核心内容", "汇总并输出最终报告"]

    logger.info("📋 [Planner] 制定了 %d 步计划: %s", len(plan), plan)
    return {"plan": plan, "past_steps": [], "iterations": 0, "replan_count": 0}


# ==========================================
# 6. 节点 2：Executor（执行器）
#    职责：内嵌 ReAct 小闭环，结合动态工具死磕单一子任务
# ==========================================
EXECUTOR_SYSTEM_PROMPT = """你是一个专注的任务执行特工，只使用提供给你的工具来完成当前子任务。

规则：
1. 你只需要解决 **当前子任务**，不要超出范围
2. 优先使用工具获取真实数据，不要凭空编造
3. 完成后，输出清晰的任务结果摘要（不超过200字）
4. 如果工具调用失败，如实说明并给出已知信息的最佳答案"""


def executor_node(state: AgentState) -> dict:
    """
    执行器节点：从 plan 取出第一个子任务，动态挂载工具，
    通过内嵌 ReAct Agent 执行，完成后更新 Memory（past_steps）。
    """
    plan = state["plan"]
    past_steps = state["past_steps"]
    current_iterations = state.get("iterations", 0) + 1

    if not plan:
        logger.warning("[Executor] 计划队列为空，跳过执行")
        return {"iterations": current_iterations}

    current_task = plan[0]
    logger.info("\n🛠️ [Executor] 执行子任务 [%d/%d]: %s", current_iterations, MAX_ITERATIONS, current_task)

    # 根据关键词动态选择工具
    active_tools = select_tools_for_task(current_task)

    # 构建内嵌 ReAct 执行特工（仅持有当前任务所需的工具）
    executor_agent = create_react_agent(model, active_tools)

    # 将历史足迹注入 context，让执行器感知已完成的工作
    context = ""
    if past_steps:
        context = "\n".join([f"- {step}: {result[:100]}..." for step, result in past_steps[-3:]])
        context = f"\n已完成的步骤摘要（最近3步）：\n{context}\n"

    execution_prompt = (
        f"{context}"
        f"你当前必须完成的子任务是：{current_task}\n"
        f"请使用工具完成该任务，并给出结果摘要。"
    )

    task_result = "[执行失败] 未能获得有效结果"
    try:
        result = executor_agent.invoke({
            "messages": [
                SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
                HumanMessage(content=execution_prompt),
            ]
        })
        # 取最后一条 AI 消息作为结果
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                task_result = msg.content
                break
    except Exception as e:
        # 单工具/单步失败：记录错误但不中断整体流程
        logger.error("[Executor] 子任务执行异常: %s", e)
        task_result = f"[执行异常] {current_task} 执行失败，错误原因：{e}，将继续后续任务。"

    logger.info("✅ [Executor] 子任务完成，结果摘要: %s...", task_result[:80])

    return {
        "past_steps": past_steps + [(current_task, task_result)],
        "plan": plan[1:],     # 从队列中移除已完成的任务
        "iterations": current_iterations,
    }


# ==========================================
# 7. 节点 3：Replanner（反思与重规划器）
#    职责：检验目标是否达成，未达成则生成补救计划
# ==========================================
REPLANNER_SYSTEM_PROMPT = """你是一名苛刻的质检官，负责评审任务完成质量。

评审规则：
1. 将执行足迹与用户的原始总目标进行比对
2. 如果圆满达成：以 'FINAL_ANSWER:' 开头输出完整的最终汇总报告
3. 如果有明显遗漏：输出补救子任务的 JSON 列表，例如 ["补充调查竞争对手信息"]
4. 判断标准从严，但不要无休止地追求完美（补救计划最多提一次）"""


def replanner_node(state: AgentState) -> dict:
    """
    反思与重规划节点：
    - 计划队列清空后触发
    - 评估总目标是否达成
    - 达成 → 输出最终答案
    - 未达成且未超出重规划上限 → 生成补救计划
    - 超出上限 → 强制输出当前最佳结果
    """
    replan_count = state.get("replan_count", 0)
    iterations = state.get("iterations", 0)

    logger.info("\n🧐 [Replanner] 开始反思，当前迭代: %d，重规划次数: %d", iterations, replan_count)

    # 防护 1：全局迭代次数超限，强制结束
    if iterations >= MAX_ITERATIONS:
        logger.warning("[Replanner] 已达 MAX_ITERATIONS=%d，强制输出当前结果", MAX_ITERATIONS)
        summary = _build_forced_summary(state)
        return {"final_answer": summary}

    # 防护 2：重规划次数超限，强制结束
    if replan_count >= MAX_REPLAN_COUNT:
        logger.warning("[Replanner] 已达 MAX_REPLAN_COUNT=%d，强制输出当前结果", MAX_REPLAN_COUNT)
        summary = _build_forced_summary(state)
        return {"final_answer": summary}

    task = state["task"]
    past_steps = state["past_steps"]

    steps_summary = "\n".join([f"{i+1}. [{step}]: {result[:150]}..." for i, (step, result) in enumerate(past_steps)])

    try:
        response = model.invoke([
            SystemMessage(content=REPLANNER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"用户原始总目标：{task}\n\n"
                f"已完成的执行足迹：\n{steps_summary}\n\n"
                f"请评审是否完美达成，并给出结论。"
            )),
        ])
        content = response.content.strip()
    except Exception as e:
        logger.error("[Replanner] LLM 调用失败，强制输出: %s", e)
        return {"final_answer": _build_forced_summary(state)}

    if "FINAL_ANSWER:" in content:
        final = content.split("FINAL_ANSWER:")[1].strip()
        logger.info("🎉 [Replanner] 目标已完美达成，输出最终报告。")
        return {"final_answer": final}

    # 尝试解析补救计划
    try:
        clean_content = content.replace("```json", "").replace("```", "").strip()
        new_plan: List[str] = json.loads(clean_content)
        if isinstance(new_plan, list) and len(new_plan) > 0:
            logger.info("⚠️ [Replanner] 发现遗漏，生成补救计划: %s", new_plan)
            return {"plan": new_plan, "replan_count": replan_count + 1}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("[Replanner] 补救计划解析失败，视为达成: %s", e)

    # 兜底：无法解析也无 FINAL_ANSWER，视为已达成
    return {"final_answer": content}


def _build_forced_summary(state: AgentState) -> str:
    """当超出迭代上限时，将已有足迹强制整合为最终输出。"""
    past_steps = state.get("past_steps", [])
    if not past_steps:
        return "任务执行超时，未能产出有效结果，请简化任务后重试。"
    lines = [f"### {step}\n{result}" for step, result in past_steps]
    return "【已达迭代上限，输出当前最佳结果】\n\n" + "\n\n".join(lines)


# ==========================================
# 8. 路由函数
# ==========================================

def route_after_execution(state: AgentState) -> str:
    """Executor 执行完一步后：有剩余计划 → 继续执行；计划清空 → 进入反思。"""
    if len(state.get("plan", [])) > 0:
        return "executor"
    return "replanner"


def route_after_replanner(state: AgentState) -> str:
    """Replanner 结束后：有最终答案 → 结束；有新计划 → 回到执行器。"""
    if state.get("final_answer"):
        return END
    return "executor"


# ==========================================
# 9. 组装 StateGraph
# ==========================================

def build_orchestrator(use_memory: bool = True):
    """
    构建 Plan-and-Execute Agent 状态机。

    Args:
        use_memory: 是否启用 SqliteSaver 持久化记忆（默认开启）

    Returns:
        编译后的 CompiledGraph 实例
    """
    workflow = StateGraph(AgentState)

    # 注册节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)

    # 连线：START → planner → executor
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")

    # 条件边：executor 完成一步后判断继续或进入反思
    workflow.add_conditional_edges(
        "executor",
        route_after_execution,
        {"executor": "executor", "replanner": "replanner"},
    )

    # 条件边：replanner 结束后判断输出或继续执行
    workflow.add_conditional_edges(
        "replanner",
        route_after_replanner,
        {END: END, "executor": "executor"},
    )

    # Memory（持久化记忆）：使用 MemorySaver 支持跨步骤状态恢复
    # 生产环境可替换为 SqliteSaver.from_conn_string("agent_memory.db")
    checkpointer = MemorySaver() if use_memory else None

    return workflow.compile(checkpointer=checkpointer)


# ==========================================
# 10. 主程序入口
# ==========================================
if __name__ == "__main__":
    app = build_orchestrator(use_memory=True)

    # 演示任务：典型的"长周期复合任务"，ReAct 单循环处理不了
    task = (
        "写一份在旧金山举办 3 天 AI 峰会的策划案。"
        "必须包含每天核心议题安排、粗略的美元预算表，"
        "并且指出本次活动最大的 2 个运营风险。"
    )

    print("\n" + "=" * 60)
    print("🚀 Plan-and-Execute Agent 启动")
    print("=" * 60)
    print(f"目标任务: {task}\n")

    # 配置会话 ID（Memory 持久化的 key）
    config = {"configurable": {"thread_id": "summit_planning_001"}}

    initial_state: AgentState = {
        "task": task,
        "plan": [],
        "past_steps": [],
        "final_answer": "",
        "iterations": 0,
        "replan_count": 0,
    }

    try:
        final_state = app.invoke(initial_state, config=config)

        print("\n" + "=" * 60)
        print("🏆 最终交付物")
        print("=" * 60)
        print(final_state.get("final_answer", "未产出最终答案"))
        print(f"\n📊 执行统计: 共 {final_state.get('iterations', 0)} 次迭代，"
              f"{len(final_state.get('past_steps', []))} 个子任务完成。")

    except Exception as e:
        logger.error("Agent 运行时全局异常: %s", e, exc_info=True)
        print(f"\n❌ Agent 运行失败: {e}")
