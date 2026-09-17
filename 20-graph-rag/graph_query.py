"""
GraphRAG & NetworkX 多跳推理与知识图谱构建模块
==================================================
技术方案：
  1. 实体关系抽取：使用 ChatOpenAI + PydanticOutputParser 生成结构化节点与边
  2. 图图谱构建：基于 NetworkX 构建内存有向图 DiGraph
  3. 多跳路径检索：计算子图/最短路径并提取实体语义关系上下文
  4. 答流结合：结合图路径上下文与大模型生成多跳推理回答
"""

import os
import json
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

# 处理 OPENAI_API_BASE 与 OPENAI_BASE_URL 兼容性
api_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
api_key = os.getenv("OPENAI_API_KEY")

# ==========================================
# 1. 定义数据结构
# ==========================================
class Node(BaseModel):
    id: str = Field(description="实体的名称，例如 '张三', '拓维信息'")
    type: str = Field(description="实体的类型，例如 'Person', 'Company', 'Location'")

class Edge(BaseModel):
    source: str = Field(description="起点实体 ID")
    target: str = Field(description="终点实体 ID")
    relation: str = Field(description="实体间关系，例如 'WORKS_FOR', 'LOCATED_IN'")

class KnowledgeGraph(BaseModel):
    nodes: List[Node] = Field(description="提取的实体节点列表")
    edges: List[Edge] = Field(description="提取的关系边列表")

# ==========================================
# 2. GraphRAG 核心引擎类
# ==========================================
class GraphRAGEngine:
    def __init__(self):
        model_name = os.getenv("MODEL_NAME", "deepseek-chat")
        self.llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0
        )
        self.parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        
        # 初始化 NetworkX 有向图
        self.graph = nx.DiGraph()

        self.prompt = PromptTemplate(
            template="""你是一个顶级的知识图谱数据抽取专家。
请阅读以下文本，识别其中提及的所有实体 (Nodes) 以及实体之间的语义关联 (Edges)。

{format_instructions}

文本内容：
{text}
""",
            input_variables=["text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        self.chain = self.prompt | self.llm | self.parser

    def build_graph_from_text(self, text: str) -> KnowledgeGraph:
        """从非结构化文本中提取实体与关系并写入 NetworkX 图"""
        kg: KnowledgeGraph = self.chain.invoke({"text": text})
        
        for node in kg.nodes:
            self.graph.add_node(node.id, type=node.type)
            
        for edge in kg.edges:
            self.graph.add_edge(edge.source, edge.target, relation=edge.relation)
            
        return kg

    def search_multihop_context(self, source_node: str, target_node: str, max_depth: int = 4) -> Dict[str, Any]:
        """使用 NetworkX 计算源实体与目标实体之间的多跳关联路径"""
        if source_node not in self.graph or target_node not in self.graph:
            return {
                "found": False,
                "reason": f"实体 '{source_node}' 或 '{target_node}' 未在图谱中找到",
                "paths": [],
                "formatted_context": ""
            }

        try:
            # 查找多条简单路径
            paths = list(nx.all_simple_paths(self.graph.to_undirected(), source=source_node, target=target_node, cutoff=max_depth))
            formatted_lines = []
            
            for idx, path in enumerate(paths):
                path_str = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    if self.graph.has_edge(u, v):
                        rel = self.graph[u][v].get("relation", "CONNECTED_TO")
                        path_str.append(f"{u} --[{rel}]--> {v}")
                    elif self.graph.has_edge(v, u):
                        rel = self.graph[v][u].get("relation", "CONNECTED_TO")
                        path_str.append(f"{v} --[{rel}]--> {u}")
                formatted_lines.append(f"路径 {idx+1}: " + " | ".join(path_str))
                
            return {
                "found": True,
                "paths": paths,
                "formatted_context": "\n".join(formatted_lines)
            }
        except nx.NetworkXNoPath:
            return {
                "found": False,
                "reason": f"在 {max_depth} 跳范围内未找到连通路径",
                "paths": [],
                "formatted_context": ""
            }

    def answer_multihop_question(self, question: str, source_node: str, target_node: str) -> str:
        """根据关联路径使用大模型回答多跳推理问题"""
        context_data = self.search_multihop_context(source_node, target_node)
        
        if not context_data["found"]:
            return f"❌ 图检索未能解决多跳关联：{context_data['reason']}"

        qa_prompt = f"""请根据以下从知识图谱中检索到的实体关联路径，精准回答用户的问题。

知识图谱路径上下文：
{context_data['formatted_context']}

用户问题：
{question}
"""
        response = self.llm.invoke(qa_prompt)
        return response.content


# ==========================================
# 3. 运行演示
# ==========================================
if __name__ == "__main__":
    text_corpus = (
        "张三是拓维信息的高级工程师，他目前在位于拓维信息AI应用开发中心的总部办公。"
        "拓维信息总部设立在湖南省长沙市麓谷高新区。"
        "李四是张三的大学同学，目前也在长沙市麓谷高新区的一家科技公司担任产品经理。"
    )

    print("📖 [1] 注入示例文本并构建知识图谱...")
    engine = GraphRAGEngine()
    kg = engine.build_graph_from_text(text_corpus)
    
    print(f"✅ 成功插入 {engine.graph.number_of_nodes()} 个节点, {engine.graph.number_of_edges()} 条边")

    question = "张三和李四有什么地理或工作上的多跳联系？"
    print(f"\n❓ [2] 多跳推理查询: '{question}'")
    
    answer = engine.answer_multihop_question(question, source_node="张三", target_node="李四")
    print(f"\n💡 [3] GraphRAG 多跳推理回答:\n{answer}")
