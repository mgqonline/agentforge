import sys
import os
sys.path.append(os.path.abspath("."))
from rag_engine import RAGEngine

rag = RAGEngine()
rag.build_or_load()
context, sources = rag.retrieve("MCP 协议解决了什么痛点？")
print("RETRIEVED CONTEXT:")
print(context)
print("SOURCES:")
print(sources)
