import os
from dotenv import load_dotenv
load_dotenv()

from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# ==========================================
# 1. 定义知识图谱的 Pydantic 数据结构
# ==========================================
class Node(BaseModel):
    id: str = Field(description="实体的唯一标识符，通常是名字，例如 'Alice', 'Google'")
    type: str = Field(description="实体的类型，例如 'Person', 'Company', 'Location'")

class Edge(BaseModel):
    source: str = Field(description="关系起点的实体ID")
    target: str = Field(description="关系终点的实体ID")
    relation: str = Field(description="两个实体之间的关系，例如 'WORKS_FOR', 'LOCATED_IN'")

class KnowledgeGraph(BaseModel):
    nodes: List[Node] = Field(description="提取出的所有实体的列表")
    edges: List[Edge] = Field(description="实体之间所有关系的列表")


from langchain_core.output_parsers import PydanticOutputParser

# ==========================================
# 2. 初始化大模型
# ==========================================
# 自动读取 .env 里的配置，回退默认值为 deepseek-v4-pro
model_name = os.getenv("MODEL_NAME", "deepseek-v4-pro")
llm = ChatOpenAI(model=model_name, temperature=0)

# 定义 Pydantic 解析器，取代强依赖底层 API 的 with_structured_output
parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)

# ==========================================
# 3. 编写 Prompt 模板
# ==========================================
# 我们必须在 prompt 里显式告诉大模型 JSON 的格式约束
prompt = PromptTemplate(
    template="""你是一个顶级的数据挖掘专家，专门负责从复杂的文本中抽取知识图谱（实体与关系）。
请阅读以下文本，并提取出所有的节点(Nodes)和边(Edges)。

{format_instructions}

文本内容：
{text}
""",
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 构建处理管道 (Chain)：大模型输出纯文本字符串 -> 解析器自动转化为 Pydantic 对象
chain = prompt | llm | parser


# ==========================================
# 4. 测试抽取效果
# ==========================================
if __name__ == "__main__":
    sample_text = (
        "张三是拓维信息的高级工程师，他目前在位于拓维信息AI应用开发中心的总部办公。"
        "李四是张三的大学同学，目前也在拓维信息AI应用开发中心的另一家科技公司担任产品经理，"
        "并且经常和拓维信息的团队有业务合作。"
    )
    
    print(f"📖 输入文本:\n{sample_text}\n")
    print("🤖 正在抽取知识图谱实体与关系...\n")
    
    # 运行大模型抽取
    graph_data: KnowledgeGraph = chain.invoke({"text": sample_text})
    
    print("🎯 [抽取的节点 Entities]")
    for node in graph_data.nodes:
        print(f"  - {node.id} ({node.type})")
        
    print("\n🔗 [抽取的关系 Relationships]")
    for edge in graph_data.edges:
        print(f"  - {edge.source} --[{edge.relation}]--> {edge.target}")
    
    print("\n✅ GraphRAG 的第一步（数据图谱化）完成！")
