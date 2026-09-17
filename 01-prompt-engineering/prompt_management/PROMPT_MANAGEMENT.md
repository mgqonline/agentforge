# Prompt 工程进阶：框架设计与版本管理

在企业级 AI 开发中，Prompt 不仅仅是“一段字符串”，而是核心的**代码资产**。既然是资产，就需要用软件工程的思维来管理它。

## 1. 核心功能点

### A. 分层 Prompt 框架设计 (Prompt Framework)
将臃肿的提示词拆分为高内聚、低耦合的模块：
*   **System Prompt (`system.prompt`)**：全局系统设定、人物画像（Persona）、通用红线原则。它极少变动。
*   **Task Prompt / 参数模板 (`task.prompt`)**：针对具体任务的指令，其中包含动态变量占位符（如 `{context}`, `{query}`）。
*   **示例库 (`examples.json`)**：Few-shot 所需的输入输出示例。将示例独立出来，方便非技术人员（如业务专家）在后台直接配置增删，而不需要改代码。

### B. 将 Prompt 当做代码管理 (Prompt as Code)
*   **Git 存储与对比**：将每一种 Prompt 层级保存为独立的文本/JSON文件。每一次修改都能通过 Git 留下 commit 记录，利用 `git diff` 能够清晰看出 v1 到 v2 到底修改了哪个定语。
*   **多版本共存 (v1 vs v2)**：系统中同时保留多个版本的文件夹。

### C. 灰度发布与 A/B 测试 (A/B Testing & Canary Release)
*   模型迭代或 Prompt 优化存在极大风险（比如修改了语气却导致幻觉率上升）。
*   利用网关路由规则（例如 `v1: 20%`, `v2: 80%`），可以让一部分流量先体验新的 Prompt 策略。通过分析埋点日志中不同版本用户的采纳率或客诉率，来决定是否全量发布 v2。

## 2. 代码演示结构

我们建立如下项目目录：
```text
prompt_management/
│
├── prompts/                # Git tracked Prompt 仓库
│   ├── v1/                 # 基础版 Prompt (简单直白)
│   │   ├── system.prompt
│   │   ├── task.prompt
│   │   └── examples.json
│   │
│   └── v2/                 # 进阶版 Prompt (加入专家人设与 CoT 思维链)
│       ├── system.prompt
│       ├── task.prompt
│       └── examples.json
│
├── demo_ab_test.py         # 核心框架与运行脚本
└── PROMPT_MANAGEMENT.md    # 也就是本文档
```

## 3. 使用方法

确保环境已准备好 `.env`，然后执行以下命令运行演示：

```bash
python 01-prompt-engineering/prompt_management/demo_ab_test.py
```

**运行预期**：
你会看到系统模拟了 3 次请求流量。每次请求会根据配置的权重（20% 路由到 v1，80% 路由到 v2）走不同的版本。
*   当命中 **v1** 时，模型输出将比较机械、简短。
*   当命中 **v2** 时，模型会先在 `<thinking>` 标签内分析退换货政策和鼠标损坏情况（CoT），随后输出极具安抚性和专业度的长段回复。

通过这种架构，以后业务方想调整客服话术，只需在 `v3` 目录中修改文本提交 Git 即可，无需改动任何核心 Python 业务逻辑！
