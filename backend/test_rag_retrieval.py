from rag_engine import rag_engine
rag_engine.build_or_load()
context, citations = rag_engine.retrieve("AI 实验室目前的员工叫什么名字？他今年多少岁了？")
print(f"Context: {context}")
print(f"Citations: {citations}")
