import asyncio
from orchestrator_graph import build_orchestrator_graph

async def ws(d):
    print(d)

g = build_orchestrator_graph(ws)
print("Compiled Graph:", g.compile())
