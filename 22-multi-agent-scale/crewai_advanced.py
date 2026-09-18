import os
from dotenv import load_dotenv

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

load_dotenv()
model_name = os.getenv("MODEL_NAME", "deepseek-v4-pro")

llm = LLM(
    model=f"openai/{model_name}",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE"),
    temperature=0.3, # 降低温度以保证工具调用的稳定性
)

# ==========================================
# 1. 定义专属企业级自定义工具 (Tools)
# ==========================================
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
    file_path = "21-multi-agent-scale/talkweb_ai_report_final.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[🔧 工具执行] 报告已成功落盘保存至: {file_path}")
    return f"文件已成功保存至 {file_path}"

# ==========================================
# 2. 赋予 Agent 物理手脚 (Tools)
# ==========================================
researcher = Agent(
    role="资深 AI 技术研究员",
    goal="结合外部趋势与拓维信息内部战略，出具 AI 报告。",
    backstory="你是拓维信息 AI 研究院的首席研究员，你总是通过调用内部知识库(Talkweb_Internal_KB_Search)来获取公司最新的技术动向。",
    tools=[talkweb_kb_search], # 绑定工具
    verbose=True,
    llm=llm
)

writer = Agent(
    role="科技专栏主笔",
    goal="基于研究数据，撰写专业且生动的文章，并最终保存到本地。",
    backstory="你负责把干涩的技术数据转化为漂亮的 Markdown 文章，在文章末尾，你总是会调用 (Save_Report_To_File) 将文章归档保存。",
    tools=[save_report], # 绑定工具
    verbose=True,
    llm=llm
)

# ==========================================
# 3. 编排高级动态流转任务
# ==========================================
task1 = Task(
    description="首先，检索拓维信息在 AI 领域的最新内部动作。然后，结合外部 Multi-Agent 技术趋势，撰写 2 条核心突破点。",
    expected_output="带有公司真实案例的 AI 技术突破点分析列表。",
    agent=researcher
)

task2 = Task(
    description="基于研究员提供的突破点，起草一篇字数约 500 字的《拓维麓谷高新 AI 战报》，并**必须调用工具**将报告保存到本地磁盘。",
    expected_output="执行保存文件工具后的成功提示信息。",
    agent=writer
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("🚀 [高阶态] 拓维信息带工具调用的 Agent 协作启动...\n")
    crew.kickoff()
    print("\n✅ 工作流完全结束，请检查 21-multi-agent-scale/ 目录下是否生成了报告文件！")
