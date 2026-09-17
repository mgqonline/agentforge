---
name: sandbox_security_guard
description: 当修改后端执行器 (sandbox_runner.py)、关卡执行逻辑、处理动态代码执行或涉及敏感凭据时自动触发此技能。用于守护执行沙箱安全边界与防范沙箱逃逸。
---

# 沙箱安全护栏与防逃逸开发准则 (Sandbox Security Guard)

本技能定义了 `ailearning` 代码沙箱与 Python 动态执行环境的安全边界、威胁模型及必检清单。

## 1. 核心威胁模型与红线

沙箱承载学员提交的任意 Python 代码，必须防范以下四大威胁向量：

1. **宿主机命令执行与进程逃逸**：
   - 严禁通过 `os.system`, `os.popen`, `subprocess`, `pty`, `shutil` 执行宿主底层系统命令。
   - 严禁通过 `getattr(...)` 或反引号等动态反射机制绕过黑名单。
2. **底层运行时探测与逃逸链**：
   - 严禁访问 `__subclasses__`, `__globals__`, `__code__`, `__builtins__` 等 Python 内部魔法属性构造逃逸链。
3. **敏感凭证窃取**：
   - 沙箱子进程仅允许最小必要环境变量（`PATH`, `OPENAI_BASE_URL` 等），绝不注入宿主内网数据库密码或全局 Secret。
   - 严禁用户代码直接读取系统环境变量中的 `API_KEY`、`TOKEN`、`SECRET`。
4. **资源耗尽攻击 (Denial of Service)**：
   - 强制硬超时：代码单次执行上限不得超过 60 秒（关卡验证可宽限至 90 秒，超时直接 SIGKILL 终止）。
   - 强制内存配额：通过 `setrlimit(RLIMIT_AS)` 限制子进程虚拟内存上限。
   - 强制输出截断：stdout 与 stderr 超过 64KB 时自动截断，防止终端内存被大文本撑爆。

## 2. 变更开发规范与执行步骤

在涉及沙箱执行逻辑修改时，必须依序执行以下标准流程：

1. **AST 预检先行**：
   - 任何新增的危险模式必须在 `backend/sandbox_runner.py` 的 `CodeSecurityAuditor` 中同步补充 AST 访问器。
2. **测试先行与覆盖**：
   - 修改后必须运行并扩充 `backend/test_sandbox_security.py`，确保已拦截用例 100% 通过。
3. **容器双向同步**：
   - 必须执行 `docker cp backend/sandbox_runner.py ailearning_backend:/app/backend/sandbox_runner.py`，确保生产容器与宿主机代码严格对齐。

## 3. 错误响应标准格式

当代码被沙箱安全策略拦截时，必须返回 HTTP 403 风格的受控响应结构，向学员提供友好的安全指引：
```json
{
  "status": "blocked",
  "stdout": "",
  "stderr": "🛡️ 安全边界策略拦截：禁止使用动态执行函数【eval()】。\n本实战平台仅允许与 AI 业务逻辑、模型调用及算法运算相关的安全代码。",
  "exit_code": 403,
  "execution_time_ms": 1.2
}
```
