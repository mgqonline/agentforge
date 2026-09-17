# AI Terminal - 前端工程 (React 版)

本项目是 AI Terminal 的现代化高并发 Web 前端架构版本，使用 React 和 Vite 构建。它被设计用于替代早期的原生 JS (Vanilla) 版本，以承载无限滚动的海量历史对话、极速的 DOM 渲染以及更复杂的代码展示 (Artifacts 面板) 能力。

## 🚀 核心特性

- **极致流畅的巨量对话**：采用 `react-virtuoso` 虚拟列表引擎，无论聊天历史累积了多少条，浏览器内存始终保持在极低水位。
- **动态流式渲染降级保护**：深度重构了 `react-markdown` 的渲染生命周期，智能切换 `SyntaxHighlighter` (用于打字机流式输出时的高效轻量渲染) 与 `@monaco-editor/react` (提供完整的全功能代码编辑支持)，从底层根除了 React DOM 嵌套崩溃的隐患。
- **现代化 UI 审美**：保留了深受好评的 Glassmorphism (拟物毛玻璃) 深色暗黑风格设计，加入优雅的 CSS 动画。
- **WebSocket 全双工通信**：直接连接后端的 FastAPI，毫秒级响应企业级大模型知识库检索 (RAG) 与 Function Calling 触发的推送流。

## 🛠️ 技术栈

- **构建工具**: [Vite](https://vitejs.dev/) (提供极速的 HMR 热更新和毫秒级冷启动)
- **核心框架**: React 18
- **UI & 样式**: 纯 Vanilla CSS (支持现代 CSS 变量和 Flexbox 布局) + Lucide React 图标
- **代码与 Markdown 解析**:
  - `react-markdown`: 负责对话内容的富文本转化
  - `react-syntax-highlighter`: 承担流式输出阶段的高性能语法高亮
  - `@monaco-editor/react`: 为代码查看、二次编辑和 Artifacts 模式提供 VS Code 级的编辑体验

## 📦 快速启动

1. 确保你的机器已安装 Node.js (推荐 v18+)。
2. 在当前 `frontend-react` 目录中打开终端，安装项目依赖：
   ```bash
   npm install
   ```
3. 启动 Vite 开发服务器：
   ```bash
   npm run dev
   ```
4. 默认情况下，前端服务将运行在 `http://localhost:5174/`，请确保同时已启动后端的 FastAPI 服务 (`ws://localhost:8000`)。

## 🧩 目录结构说明

- `src/App.jsx` - 顶层状态管理器，维护与后端的 WebSocket 状态机、对话列表、全局副作用处理。
- `src/MainChat.jsx` - 主聊天区域容器，包含 React-Virtuoso 虚拟长列表的核心渲染逻辑。
- `src/Sidebar.jsx` - 侧边栏历史记录组件，支持聊天隔离和清除交互。
- `src/Message.jsx` - 智能消息体组件，支持 System/User 两端排版区分，并自带 Markdown 崩溃保护渲染器。
- `src/index.css` - 全局样式系统、动画定义与颜色字典。
