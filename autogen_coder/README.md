# AutoGen 代码助手实验 (AutoGen Code Assistant)

## 背景
根据 AI 工程基础学习指南的“实践驱动”和“文档先行”原则，我们使用 AutoGen (v0.2/v0.4架构体系) 构建了一个基本的代码助手 Agent。
该 Agent 接入了 DeepSeek 模型（依据标准 Agent 构建指南中的模型默认配置建议），实现自动写代码、自动本地执行、自动 Debug 的闭环。

## 模块结构
- `coder_agent.py`: 主入口。包含了 `AssistantAgent`（大脑，负责写代码）和 `UserProxyAgent`（沙盒执行者，负责跑代码）。
- `workspace/`: 运行时动态创建的隔离目录（沙盒），防止 Agent 乱改宿主机上的关键文件。

## 实验目的
验证基于 Multi-Agent 架构下的 "Human-out-of-loop / Human-in-loop" 执行链路：
1. 大模型能否准确生成带有 Markdown 标记 (```python) 的可执行代码。
2. `LocalCommandLineCodeExecutor` 能否正确提取、执行代码。
3. 执行报错时，报错日志能否顺利传回给 `AssistantAgent` 触发自修复 (Self-healing)。

## 如何运行
1. 请确保你的 Python 环境版本 >= 3.10
2. 安装依赖：
   ```bash
   pip install pyautogen
   ```
3. 导出你的 API Key（如果使用的是默认的 DeepSeek 配置）：
   ```bash
   export DEEPSEEK_API_KEY="your-api-key"
   ```
4. 执行脚本：
   ```bash
   python coder_agent.py
   ```

## 学习笔记与踩坑记录 (TODO)
- *这里留作之后运行中遇到坑时的补充记录区。比如依赖版本冲突、执行权限不足等问题...*
