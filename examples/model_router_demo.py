import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch

# 加载环境变量
if "OPENAI_API_KEY" not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()

# ==========================================
# 1. 定义路由数据结构 (使用 Pydantic 进行强类型约束)
# ==========================================
class RouteQuery(BaseModel):
    """用于判定用户问题所属领域的路由模型"""
    domain: Literal["math", "coding", "general"] = Field(
        ...,
        description="根据用户的请求，将其分类到最合适的领域：'math'(数学), 'coding'(编程), 或 'general'(通用)."
    )

# ==========================================
# 2. 初始化大模型实例
# ==========================================
# 尝试从环境变量获取模型名称，默认适配你的 .env 配置 (DeepSeek)
model_name = os.getenv("MODEL_NAME", "deepseek-chat")

# 路由器模型：使用速度快、成本低的轻量级模型。
router_llm = ChatOpenAI(model=model_name, temperature=0)

# 专家模型：在实际企业架构中，这里可以换成不同的模型 (比如 coding_llm 可以配置为 deepseek-coder)
# 这里为了演示，我们使用同一个模型实例，但赋予不同的专家 Prompt
expert_llm = ChatOpenAI(model=model_name, temperature=0.7)

# ==========================================
# 3. 构建核心路由节点 (Router Node)
# ==========================================
# 使用 Pydantic 解析器来兼容不支持原生 `json_schema` format 的第三方大模型 (例如 DeepSeek)
parser = PydanticOutputParser(pydantic_object=RouteQuery)

route_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个高效的意图分类和模型路由器。请仔细阅读用户问题并分类到最合适的专家域。\n{format_instructions}"),
    ("human", "{question}")
]).partial(format_instructions=parser.get_format_instructions())

# 绑定 json_object 格式输出，确保模型输出合法的 JSON 字符串
router_llm_json = router_llm.bind(response_format={"type": "json_object"})

# 路由链：输入 question -> 提示词装载 -> 模型输出 JSON -> Pydantic 解析为 RouteQuery 对象
router_chain = route_prompt | router_llm_json | parser

# ==========================================
# 4. 构建领域专家处理链 (Expert Chains)
# ==========================================
# -> 4.1 数学专家
math_template = """你是一位严谨的数学家。
在回答时，必须先给出清晰的推导步骤，最后再给出答案。
问题: {question}"""
math_chain = ChatPromptTemplate.from_template(math_template) | expert_llm

# -> 4.2 编程专家
coding_template = """你是一位资深的架构师兼顶级程序员。
在回答时，请直接给出包含注释的优质代码，并对核心逻辑做简短说明，不要说多余的废话。
问题: {question}"""
coding_chain = ChatPromptTemplate.from_template(coding_template) | expert_llm

# -> 4.3 通用专家
general_template = """你是一个乐于助人的 AI 助手。
问题: {question}"""
general_chain = ChatPromptTemplate.from_template(general_template) | expert_llm

from langchain_core.runnables import RunnableBranch, RunnableLambda

# ==========================================
# 5. 构建路由分支 (RunnableBranch)
# ==========================================
def print_routing_info(info: dict) -> dict:
    """这是一个中间件：用于在控制台打印路由过程"""
    domain = info["domain"]
    print(f"\n[Router] 🧭 判定领域: <{domain.upper()}> -> 正在唤醒对应专家...")
    return info

# LCEL 的精髓：构建完整的执行计算图
full_chain = (
    # 第一步：计算路由分类，并将分类结果 domain 与原问题 question 拼装到一个字典中
    {
        "domain": router_chain | (lambda x: x.domain),
        "question": lambda x: x["question"]
    }
    # 打印日志
    | RunnableLambda(print_routing_info)
    # 第二步：根据 domain 走不同的分支链路
    | RunnableBranch(
        (lambda x: x["domain"] == "math", math_chain),
        (lambda x: x["domain"] == "coding", coding_chain),
        general_chain
    )
)

if __name__ == "__main__":
    print("🚀 启动模型路由器架构测试...")
    
    # 准备三种不同领域的测试问题
    test_questions = [
        "用 Python 实现一个带有错误重试机制的装饰器",
        "计算函数 f(x) = x^3 - 2x^2 + x 的一阶导数，并在 x=2 时的值是多少？",
        "第一次去北京旅游，有没有什么好吃的推荐？"
    ]
    
    for q in test_questions:
        print("-" * 60)
        print(f"👤 用户提问: {q}")
        
        # 调用包含路由与分发的完整流水线
        response = full_chain.invoke({"question": q})
        
        print(f"🤖 专家回复:\n{response.content}\n")
