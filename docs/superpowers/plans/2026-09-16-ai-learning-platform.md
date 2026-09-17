# AI 工程师实战工作台 (AI Learning Lab) 落地实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有的 24 阶段 AI 工程代码库改造成具备企业级可靠性、Linear 级现代暗黑极客视觉感与 LeetCode 沉浸式编码体验的“AI 实战工作台产品”。

**Architecture:** 后端提供课程目录自动索引引擎 (`curriculum_engine.py`) 与受限进程级安全沙箱 (`sandbox_runner.py`)，并通过 FastAPI 暴露课程、运行及评测接口；前端基于 React 19 + Monaco Editor + Lucide 构建现代暗黑三栏工作台（左栏路线图、中栏实验指南、右栏 Monaco 代码编辑器与执行终端），并无缝集成 DFL 决策反馈 AI 导师进行实时代码评审与错误诊断。

**Architecture Diagram:**

```mermaid
graph TD
    subgraph 前端工作台 [Frontend React 19 / Monaco / Tailwind]
        Nav[CurriculumNav 关卡树] --> Guide[MissionGuide 实验指引]
        Guide --> Editor[CodeConsole 编辑器与终端]
        Editor --> Mentor[AIMentor DFL 伴学]
    end

    subgraph 后端服务 [FastAPI Container Port 6001]
        API[/api/v1/curriculum] --> Engine[curriculum_engine.py]
        Engine --> Files[扫描 24 阶段目录 01-prompt 到 23-edge-ai]
        SandboxAPI[/api/v1/sandbox/run] --> Sandbox[sandbox_runner.py 隔离执行]
        MentorAPI[/api/v1/mentor/review] --> DFL[dfl_engine.py + LLM 诊断]
    end

    Editor -->|运行代码/评测| SandboxAPI
    Editor -->|代码诊断/提示| MentorAPI
    Nav -->|获取目录与元数据| API
```

**Tech Stack:**
- 前端: React 19, Vite, `@monaco-editor/react`, `lucide-react`, `react-markdown`, CSS Variables (Linear Dark Theme)
- 后端: Python 3.10+, FastAPI, `subprocess` (Resource Quotas: `resource.RLIMIT_AS`, `resource.RLIMIT_CPU`), Pydantic
- 容器编排: Docker Compose (后端 6001, 前端 6002/6000)

## Global Constraints
- 必须使用简体中文回复。
- 严禁破坏现有 Docker 发布体系 (`backend` 端口 6001，`frontend` 端口 6002 优先，6000 备用)。
- 代码沙箱必须具备严格的安全熔断机制（10 秒超时终止，禁止任意系统删除命令，限制内存使用）。
- 前端保持无外部破坏性依赖，必须通过 Vite 正常构建。

---

### Task 1: 后端课程解析引擎 (Curriculum Engine)

**Files:**
- Create: `backend/curriculum_engine.py`
- Test: `backend/test_curriculum_sandbox.py`

**Interfaces:**
- Consumes: 本地 `01-prompt-engineering` ~ `23-edge-ai` 目录文件
- Produces: 
  - `get_all_phases() -> List[Dict[str, Any]]`: 返回全部 24 个阶段的 id、title、order、tags、is_locked
  - `get_phase_detail(phase_id: str) -> Dict[str, Any]`: 返回该阶段的 Markdown 文档、默认 starter_code、测试文件内容与目标清单

- [ ] **Step 1: 编写失败的单元测试**

在 `backend/test_curriculum_sandbox.py` 中编写 `test_curriculum_engine_get_phases` 和 `test_curriculum_engine_get_detail`：
```python
import pytest
from curriculum_engine import CurriculumEngine

def test_get_all_phases():
    engine = CurriculumEngine(base_dir=".")
    phases = engine.get_all_phases()
    assert len(phases) >= 20
    assert any("prompt" in p["id"] for p in phases)
    first = phases[0]
    assert "id" in first
    assert "title" in first
    assert "order" in first

def test_get_phase_detail():
    engine = CurriculumEngine(base_dir=".")
    detail = engine.get_phase_detail("01-prompt-engineering")
    assert detail is not None
    assert "guide_markdown" in detail
    assert "starter_code" in detail
```

- [ ] **Step 2: 运行测试并验证失败**

运行：`pytest backend/test_curriculum_sandbox.py -v`  
预期：FAIL (ModuleNotFoundError: No module named 'curriculum_engine')

- [ ] **Step 3: 编写 `backend/curriculum_engine.py` 实现**

解析阶段目录，读取 `README.md`，提取 Python 源码作为 starter code，组装结构化元数据。

- [ ] **Step 4: 重新运行测试并验证通过**

运行：`pytest backend/test_curriculum_sandbox.py -v`  
预期：PASS

- [ ] **Step 5: 提交更改**

```bash
git add backend/curriculum_engine.py backend/test_curriculum_sandbox.py
git commit -m "feat(curriculum): implement curriculum indexing engine"
```

---

### Task 2: 后端隔离安全沙箱与执行 API (Sandbox Runner)

**Files:**
- Create: `backend/sandbox_runner.py`
- Modify: `backend/test_curriculum_sandbox.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: 用户编写的 Python 代码字符串 `code` 与可选的 `timeout_seconds`
- Produces:
  - `run_code(code: str, timeout: int = 10) -> Dict[str, Any]`: 返回 `{status: 'success'|'error'|'timeout', stdout: str, stderr: str, execution_time_ms: float}`
  - `verify_phase(phase_id: str, user_code: str) -> Dict[str, Any]`: 将用户代码与该阶段内置测试用例拼装并运行，返回测试通过详情

- [ ] **Step 1: 编写沙箱执行器的单元测试**

在 `backend/test_curriculum_sandbox.py` 中追加测试：
```python
from sandbox_runner import SandboxRunner

def test_sandbox_run_success():
    runner = SandboxRunner()
    result = runner.run_code("print('Hello AI Lab')")
    assert result["status"] == "success"
    assert "Hello AI Lab" in result["stdout"]

def test_sandbox_run_timeout():
    runner = SandboxRunner()
    result = runner.run_code("import time\ntime.sleep(3)", timeout=1)
    assert result["status"] == "timeout"
```

- [ ] **Step 2: 运行测试并确认失败**

运行：`pytest backend/test_curriculum_sandbox.py -k "test_sandbox" -v`  
预期：FAIL (ModuleNotFoundError: No module named 'sandbox_runner')

- [ ] **Step 3: 编写 `backend/sandbox_runner.py` 实现**

使用临时隔离文件、`subprocess.run`，设置超时限制与 stdout/stderr 捕获。
在 `backend/main.py` 中注册路由：
- `GET /api/v1/curriculum/phases`
- `GET /api/v1/curriculum/phases/{phase_id}`
- `POST /api/v1/sandbox/run`
- `POST /api/v1/sandbox/verify`
- `POST /api/v1/mentor/review` (接入 DFL 与 DeepSeek 分析代码)

- [ ] **Step 4: 运行全部单元测试确保通过**

运行：`pytest backend/test_curriculum_sandbox.py -v`  
预期：全部 PASS

- [ ] **Step 5: 提交更改**

```bash
git add backend/sandbox_runner.py backend/main.py backend/test_curriculum_sandbox.py
git commit -m "feat(sandbox): implement secure code execution and evaluation API"
```

---

### Task 3: 前端设计系统规范与极客暗黑主题 (Linear Theme & CSS)

**Files:**
- Modify: `frontend-react/src/index.css`
- Modify: `frontend-react/src/App.css`

**Interfaces:**
- Produces: 全局 CSS 变量（`--bg-canvas`, `--bg-surface`, `--border-subtle`, `--accent-primary`, `--accent-glow`, `--text-primary` 等）以及发光卡片、毛玻璃质感、滚动条样式和网格背景。

- [ ] **Step 1: 检查现有 CSS 并引入 Linear 暗黑主题变量**

在 `frontend-react/src/index.css` 中注入现代暗黑主题变量与精致边框微发光样式。

- [ ] **Step 2: 执行前端构建验证无样式语法错误**

在 `frontend-react` 执行：`npm run build`  
预期：Build successfully.

- [ ] **Step 3: 提交更改**

```bash
git add frontend-react/src/index.css frontend-react/src/App.css
git commit -m "style(theme): inject Linear dark geek aesthetic design tokens"
```

---

### Task 4: 前端关卡导航与实验指导书组件 (CurriculumNav & MissionGuide)

**Files:**
- Create: `frontend-react/src/components/Workbench/CurriculumNav.jsx`
- Create: `frontend-react/src/components/Workbench/MissionGuide.jsx`
- Create: `frontend-react/src/components/Workbench/HeaderBar.jsx`

**Interfaces:**
- Consumes: 后端 `/api/v1/curriculum/phases` 与 `/api/v1/curriculum/phases/{phase_id}`
- Produces:
  - `HeaderBar`: 顶部品牌、学习进度条、沙箱就绪指示、搜索快捷键
  - `CurriculumNav`: 24 阶段树状卡片、通关徽章、阶段难度标签
  - `MissionGuide`: Markdown 指南展示、核心概念卡、任务 Checklist

- [ ] **Step 1: 编写组件并支持加载远端数据与 fallback 模拟数据**
- [ ] **Step 2: 验证组件在 Vite 下正常编译**
- [ ] **Step 3: 提交更改**

```bash
git add frontend-react/src/components/Workbench/
git commit -m "feat(workbench): add HeaderBar, CurriculumNav, and MissionGuide components"
```

---

### Task 5: 前端 Monaco 代码实战台、控制台与 AI 导师组件 (CodeConsole & AIMentor)

**Files:**
- Create: `frontend-react/src/components/Workbench/CodeConsole.jsx`
- Create: `frontend-react/src/components/Workbench/AIMentorPanel.jsx`
- Modify: `frontend-react/src/App.jsx`

**Interfaces:**
- Consumes:
  - Monaco Editor 用户输入
  - 后端 `/api/v1/sandbox/run` 与 `/api/v1/sandbox/verify`
  - 后端 `/api/v1/mentor/review`
- Produces:
  - 代码一键运行 (`Cmd + Enter`)
  - 终端标准输出与错误栈高亮
  - 测试用例通过率仪表盘 (e.g. 3/3 Passed)
  - AI 导师智能诊断与思维引导抽屉

- [ ] **Step 1: 编写 CodeConsole 与 AIMentorPanel 组件**
- [ ] **Step 2: 在 App.jsx 中装配三栏沉浸式实战工作台**
- [ ] **Step 3: 本地构建测试 `npm run build` 并确认通过**
- [ ] **Step 4: 提交更改**

```bash
git add frontend-react/src/components/Workbench/ frontend-react/src/App.jsx
git commit -m "feat(workbench): assemble Monaco lab console and AI mentor integration"
```

---

### Task 6: 全链路联调与自动化部署测试

**Files:**
- Modify: `deploy.sh` (若有必要)
- Test: 全系统端到端验证

- [ ] **Step 1: 启动后端并运行沙箱测试**
- [ ] **Step 2: 构建前端静态资源并部署**
- [ ] **Step 3: 使用 curl / 浏览器请求验证 http://localhost:6002 工作台交互正常**
- [ ] **Step 4: 记录验收成果并提交**
