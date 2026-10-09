import os
from dotenv import load_dotenv

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

load_dotenv()

# ==========================================================================
# 【关键工程约束】重型第三方 SDK 必须"软导入 + 惰性构造"
# --------------------------------------------------------------------------
# crewai 是体积巨大的可选依赖（会拉起 litellm / chromadb / 大量 Agent 运行时）。
# 如果在模块顶层直接 `from crewai import ...`，那么只要当前环境没装 crewai，
# 整个模块都会 ImportError —— 连本文件里那些完全不依赖 crewai 的纯逻辑函数
# （提示词模板拼装、报告目录规划等）也都无法被导入和单元测试。
# 因此这里把可选依赖收敛到 _load_crewai()，并给出可操作的中文安装指引。
# ==========================================================================
_INSTALL_HINT = (
    "本关卡需要 CrewAI 运行时，请先安装依赖：\n"
    "    pip install crewai crewai-tools\n"
    "安装后重新运行本脚本即可。"
)

_crewai_cache = {}


def _load_crewai():
    """惰性加载 CrewAI 运行时（未安装时抛出带安装指引的 RuntimeError）"""
    if not _crewai_cache:
        try:
            from crewai import Agent, Task, Crew, Process, LLM  # noqa: F401
            from crewai.tools import tool  # noqa: F401
        except ImportError as exc:  # pragma: no cover - 取决于本地依赖环境
            raise RuntimeError(f"{_INSTALL_HINT}\n原始错误: {exc}") from exc
        _crewai_cache.update(
            {"Agent": Agent, "Task": Task, "Crew": Crew, "Process": Process, "LLM": LLM, "tool": tool}
        )
    return _crewai_cache


# ==========================================================================
# 1. 纯逻辑层：不依赖任何重型 SDK，永远可导入、可测试
# ==========================================================================
def build_report_path(output_dir: str = "22-multi-agent-scale", filename: str = "talkweb_ai_report_final.md") -> str:
    """拼装最终研报的落盘路径（统一收敛路径规则，避免硬编码散落各处）"""
    return os.path.join(output_dir, filename)


def build_research_brief(focus_keywords: list) -> str:
    """把研究方向关键词组装成给研究员的动态任务描述"""
    keywords_text = "、".join(str(k).strip() for k in focus_keywords if str(k).strip())
    return (
        f"检索拓维信息在【{keywords_text}】方向的最新内部动作，"
        "并结合外部 Multi-Agent 技术趋势，给出 2 条核心突破点。"
    )


def summarize_multi_agent_payloads(results: list, main_topic: str) -> str:
    """纯函数版 Map-Reduce 归约：把所有子 Agent 的产出合并成终稿骨架"""
    cleaned = [str(r) for r in results if str(r).strip()]
    if not cleaned:
        return f"【{main_topic}】暂无有效子任务产出。"
    return f"【{main_topic} 终极财报】\n根据收集的数据: " + " | ".join(cleaned)


def get_model_name() -> str:
    """读取本关卡使用的模型名（默认回退到 DeepSeek）"""
    return os.getenv("MODEL_NAME", "deepseek-v4-pro")


def build_llm():
    """惰性构造 LLM：未安装 crewai 时给出明确指引，而不是 ImportError 崩溃"""
    LLM = _load_crewai()["LLM"]
    model_name = get_model_name()
    # 注意：沙箱安全边界禁止在代码里直接读取带 KEY 字样的环境变量（如 OPENAI_API_KEY）。
    # LiteLLM / OpenAI SDK 会自动从环境变量读取凭据，这里无需显式传 api_key。
    return LLM(
        model=f"openai/{model_name}",
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0.3,  # 降低温度以保证工具调用的稳定性
    )


# ==========================================================================
# 2. 定义专属企业级自定义工具 (Tools)
# ==========================================================================
def _build_tools():
    """惰性构造 CrewAI 工具对象（依赖 crewai 的 @tool 装饰器）"""
    runtime = _load_crewai()
    tool = runtime["tool"]

    @tool("Talkweb_Internal_KB_Search")
    def talkweb_kb_search(query: str) -> str:
        """
        当需要查询拓维信息(Talkweb)的内部战略、历史项目或技术栈储备时使用此工具。
        输入参数为查询关键字。
        """
        # 真实场景下，这里会调用 04-rag 模块或者 20-graph-rag 模块的查询接口
        print(f"\n[🔧 工具执行] 正在检索拓维内部知识库，关键词: {query}")
        if "AI" in query or "智能" in query:
            return "【内部机密】拓维信息在拓维信息AI应用开发中心近期落地了'交通大模型'与'工业质检Agent'，正加速从传统 IT 服务向 AI 智能底座转型。"
        return "未找到相关内部机密记录。"

    @tool("Save_Report_To_File")
    def save_report(content: str) -> str:
        """
        当你完成报告定稿后，必须使用此工具将内容保存到本地磁盘。
        输入参数为 Markdown 格式的完整报告内容。
        """
        file_path = build_report_path("21-multi-agent-scale")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n[🔧 工具执行] 报告已成功落盘保存至: {file_path}")
        return f"文件已成功保存至 {file_path}"

    return talkweb_kb_search, save_report


# ==========================================================================
# 3. 编排层：赋予 Agent 物理手脚并组装 Crew
# ==========================================================================
def build_crew():
    """组装研究员 + 主笔的双 Agent 顺序协作流（仅在真正要跑 Crew 时才调用）"""
    runtime = _load_crewai()
    Agent, Task, Crew, Process = (
        runtime["Agent"], runtime["Task"], runtime["Crew"], runtime["Process"]
    )
    talkweb_kb_search, save_report = _build_tools()
    llm = build_llm()

    researcher = Agent(
        role="资深 AI 技术研究员",
        goal="结合外部趋势与拓维信息内部战略，出具 AI 报告。",
        backstory="你是拓维信息 AI 研究院的首席研究员，你总是通过调用内部知识库(Talkweb_Internal_KB_Search)来获取公司最新的技术动向。",
        tools=[talkweb_kb_search],  # 绑定工具
        verbose=True,
        llm=llm,
    )

    writer = Agent(
        role="科技专栏主笔",
        goal="基于研究数据，撰写专业且生动的文章，并最终保存到本地。",
        backstory="你负责把干涩的技术数据转化为漂亮的 Markdown 文章，在文章末尾，你总是会调用 (Save_Report_To_File) 将文章归档保存。",
        tools=[save_report],  # 绑定工具
        verbose=True,
        llm=llm,
    )

    task1 = Task(
        description=build_research_brief(["AI", "智能体"]),
        expected_output="带有公司真实案例的 AI 技术突破点分析列表。",
        agent=researcher,
    )

    task2 = Task(
        description="基于研究员提供的突破点，起草一篇字数约 500 字的《拓维麓谷高新 AI 战报》，并**必须调用工具**将报告保存到本地磁盘。",
        expected_output="执行保存文件工具后的成功提示信息。",
        agent=writer,
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[task1, task2],
        process=Process.sequential,
        verbose=True,
    )


def run_multi_agent_workflow():
    """对外统一入口：启动带工具调用的多 Agent 协作"""
    print("🚀 [高阶态] 拓维信息带工具调用的 Agent 协作启动...\n")
    crew = build_crew()
    crew.kickoff()
    print("\n✅ 工作流完全结束，请检查 21-multi-agent-scale/ 目录下是否生成了报告文件！")


if __name__ == "__main__":
    run_multi_agent_workflow()
