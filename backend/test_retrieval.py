import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from rag_engine import rag_engine

query = "AI 实验室目前的员工叫什么名字？他今年多少岁了？"
print("Query:", query)
context, sources = rag_engine.retrieve(query, k=5)
print("Context:")
print(context)
print("Sources:")
print(sources)
