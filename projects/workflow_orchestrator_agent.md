# 生产级工作流编排 Agent (Workflow Orchestrator) 架构需求规格说明书

**更新时间**：2026-07-20  
**核心定位**：基于 LangGraph 的强约束工作流编排专家，主要负责接收复杂的业务指令，拆解子任务并精准控制外部系统的 API 调用。

---

## 一、 系统架构选型 (Architecture Design)

### 1. 引擎基座：LangGraph State Machine (状态机编排)
- **弃用原生 ReAct**：放弃完全依赖 LLM 原生 Function Calling 的无边界发散循环模式，避免由于工具返回异常而导致模型陷入“死循环思考”或幻觉操作。
- **图节点约束**：将核心的业务流转（如：意图识别 -> 参数组装 -> API请求 -> 结果解析）硬编码为图的 `Nodes` (节点) 和 `Edges` (连线)。
- **决策下放**：大模型仅在具体的图节点内部负责局部路由判断与参数提取，保证了整个主干流程 100% 的可追溯性和极高的确定性。

### 2. 算力分配与模型分流 (Router & Executor Pattern)
由于单一超大模型不仅成本高昂，且处理特定格式提取的耗时较长，系统采用“大小模型分级协作”的模式：
- **Router Node (中枢路由大脑)**：使用高智商模型（如 GPT-4o / Claude 3.5 Sonnet 等级别），仅部署在入口节点，负责复杂的意图抽取与全局路由分支判断。
- **Executor Node (干活手脚小模型)**：针对 API 参数组装、脏数据 JSON 清洗等纯格式化“体力活”，交由快速、低成本的小规模参数模型（如 Llama3-8B 级别或本地微调模型），并配合 Few-Shot Prompt 来保障极高的并发吞吐量与极低延迟。

---

## 二、 记忆与状态管理 (State Management)

### 1. 记忆瘦身机制 (Structured State Schema)
- **问题背景**：外部 API 返回的 Raw JSON 动辄上百 KB，如果使用传统的 `Append-only` 对话历史模式，极易撑爆上下文窗口，导致大模型出现“注意力漂移 (Attention Drift)”。
- **按需裁剪策略**：
  - 在全局 `State` 中不再存放无差别的 Message History，而是严格定义强类型的业务字段（如 `parsed_intent`, `current_step`, `clean_api_result`）。
  - **中间件过滤**：设立专属的 `Response Parser Layer` 过滤层，在外部系统返回结果存入 State 之前，强制提纯并剥离冗余字段，确保下一个 Node 中的大模型每次看到的都是最高密度的核心上下文数据。

---

## 三、 安全容错与人机协同 (Fault Tolerance & Safety)

### 1. 高风险 API 拦截 (Human-in-the-loop)
- 针对具有破坏性或高度敏感的外部操作（例如：资金划扣、核心数据删除、群发触达），系统中必须存在硬编码的断点拦截节点 (`Interrupt Node`)。
- 当图流转到该类节点前，执行状态挂起，通过向管理员推送摘要请求，等待人工审查批准 (Approve) 后方可放行。

### 2. 专属回退降级策略 (Fallback Nodes)
- **熔断机制**：当外部请求遇到网络超时、鉴权失败等异常时，不依赖 LLM 盲目自我猜测并浪费 Token 重试。
- **定向 Fallback**：由底层的捕获机制直接引导流转到专属的 `Fallback Node` 进行熔断保护，针对特定的错误码执行提前预演的安全降级方案（如读取缓存、重定向任务或中止并返回结构化报错详情）。

---

## 四、 核心工作流示意 (Workflow Diagram)

```mermaid
graph TD
    A[用户指令输入] --> B[Router Node: 大模型进行意图识别]
    B -->|判断为查询任务| C[Query Builder Node: 小模型构造参数]
    B -->|判断为写入任务| D[Safety Check: 拦截与校验]
    
    C --> E[执行 API 请求]
    
    D --> F{人机协同 (HITL) 审批}
    F -->|拒绝| Z[流程中止]
    F -->|通过| E
    
    E -->|成功返回庞大数据| G[Parser Node: 小模型字段清洗与状态瘦身]
    E -->|异常报错| H[Fallback Node: 错误分类与熔断降级]
    
    G --> I[汇总结果返回至用户]
    H --> I
```
