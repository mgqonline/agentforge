import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from main import build_workflow, AgentState

app = FastAPI(
    title="Workflow Orchestrator Agent API",
    description="基于 LangGraph 搭建的智能编排 Agent 服务",
    version="1.0"
)

# 挂载静态前端页面
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")

# 在内存中预编译好 Agent Graph
agent_app = build_workflow()

# 客户端请求格式
class TaskRequest(BaseModel):
    task: str
    is_approved: bool = False # 默认不授权（遇到高风险会走熔断逻辑）

class TaskResponse(BaseModel):
    intent: str
    requires_approval: bool
    final_response: str
    clean_data: dict | None = None
    api_params: dict | None = None

@app.post("/api/v1/execute", response_model=TaskResponse)
def execute_task(req: TaskRequest):
    """
    提交一条任务指令给 Agent 编排引擎处理。
    如果包含'删除'等高危字眼且 `is_approved=False`，将会触发 HITL 安全熔断。
    """
    initial_state = {
        "input_task": req.task,
        "is_approved": req.is_approved
    }
    
    try:
        # 同步调用 Agent
        result = agent_app.invoke(initial_state)
        
        return TaskResponse(
            intent=result.get("parsed_intent", "UNKNOWN"),
            requires_approval=result.get("requires_approval", False),
            final_response=result.get("final_response", ""),
            clean_data=result.get("clean_api_result"),
            api_params=result.get("api_params")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 正在启动 Agent 编排服务...")
    print("👉 接口文档地址: http://127.0.0.1:8000/docs")
    # 启动 Uvicorn HTTP 服务
    uvicorn.run(app, host="127.0.0.1", port=8000)
