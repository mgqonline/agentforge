import os
from dotenv import load_dotenv

# 完全禁用 CrewAI 与 OpenTelemetry 的匿名遥测上传，防止触发本地 SSL 阻断
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent, Task, Crew, Process, LLM

# 1. 加载环境变量与大模型配置
load_dotenv()
model_name = os.getenv("MODEL_NAME", "deepseek-v4-pro")

# CrewAI 新版 (>=0.30) 要求使用其内置的 LLM (基于 LiteLLM) 而非 LangChain 的 ChatOpenAI
# 我们通过 "openai/" 前缀来兼容第三方类 OpenAI 接口 (如 DeepSeek)
llm = LLM(
    model=f"openai/{model_name}",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE"),
    temperature=0.7,
)

# ==========================================
# 2. 定义角色 (Agents)
# ==========================================
researcher = Agent(
    role="资深 AI 技术研究员",
    goal="全面调研 2026 年最新的人工智能前沿技术发展趋势。",
    backstory=(
        "你是拓维信息（位于拓维信息AI应用开发中心）AI 研究院的首席研究员。"
        "你不仅对大模型、多模态、AI Agent 等技术了如指掌，"
        "还非常擅长分析这些技术如何赋能企业级数字化转型。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm
)

writer = Agent(
    role="科技专栏主笔",
    goal="将研究员汇总的技术资料转化为一篇引人入胜、结构清晰的内部参考报告。",
    backstory=(
        "你目前就职于拓维信息AI应用开发中心的拓维信息总部。"
        "你擅长用生动的语言将深奥的 AI 技术原理解释给业务部门的同事听。"
        "你的行文风格专业但不失幽默，且一定要在文章中体现拓维信息的本土特色和创新精神。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm
)

reviewer = Agent(
    role="内容质量总监",
    goal="严格审核报告的逻辑严密性、技术准确度，以及是否符合公司价值观。",
    backstory=(
        "你是拓维信息的质量把控专家，工作极其严谨。"
        "你会检查报告中是否出现了技术术语误用，段落结构是否合理，"
        "并确保全文紧紧围绕'立足长沙麓谷，放眼全球前沿'的主旨。"
        "如果发现问题，你会直接修改并输出最终的完美版本。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# ==========================================
# 3. 定义任务 (Tasks)
# ==========================================
task1 = Task(
    description=(
        "撰写一份关于『2026年 AI 前沿技术发展』的研究纪要。"
        "重点关注：1. 复杂多智能体协同技术；2. 端侧 AI 部署；3. 高阶 GraphRAG。"
        "提炼出这三项技术的 3 个核心商业突破口。"
    ),
    expected_output="一份包含 3 个核心商业突破口的详细技术纪要（Markdown 格式）。",
    agent=researcher
)

task2 = Task(
    description=(
        "基于研究员提交的纪要，起草一份完整的《拓维信息内部 AI 参阅报告》。"
        "文章必须分为：引言（结合长沙麓谷的高科技氛围）、技术拆解（通俗易懂）、未来展望（结合公司业务）。"
    ),
    expected_output="一篇字数不少于 800 字的结构化内部报告初稿。",
    agent=writer
)

task3 = Task(
    description=(
        "审阅主笔提交的报告初稿。"
        "1. 修正所有语病和技术错误；"
        "2. 提升语言的专业度和感染力；"
        "3. 确保整篇文章体现了拓维信息在行业的领先定位。"
        "输出最终定稿直接用于发表。"
    ),
    expected_output="终稿报告（Markdown 格式），无任何批注，直接呈现正文。",
    agent=reviewer
)

# ==========================================
# 4. 组建团队并执行流程 (Crew)
# ==========================================
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[task1, task2, task3],
    # Process.sequential 表示任务按顺序依次执行
    # 后一个任务的 agent 能够自动获取前一个任务的输出作为上下文
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("🚀 [拓维信息 AI 实验室] 多智能体协同项目启动...\n")
    # kickoff 开始干活
    result = crew.kickoff()
    
    print("\n==========================================")
    print("✅ 团队协作完成！最终交付报告如下：")
    print("==========================================\n")
    print(result)
