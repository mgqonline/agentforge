# 🔐 AgentForge · 预置多租户账号与权限治理凭据手册

> **文档定位**：项目开发测试、演示打靶与多租户权限体验专属账号清单  
> **更新时间**：2026-09-16  
> **访问入口**：
> - 💻 **Web 实战工作台 (双端口通道均可访问)**：
>   - 主推荐入口：[http://localhost:6000](http://localhost:6000)
>   - 兼容通道入口：[http://localhost:6002](http://localhost:6002)
> - 📚 **后端 OpenAPI 接口契约**：[http://localhost:6001/docs](http://localhost:6001/docs)

---

## 📌 一、 预置多租户账号矩阵速查

| 账号身份 | 用户名 (Username) | 登录密码 (Password) | 所属租户 (Tenant) | 角色定位 (Role) | 核心权限与业务特性 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **👑 超级管理员 (最高权限)** | `admin` | `AgentForge@2026` | **企业核心智算中心**<br>`tenant_enterprise_core` | **超级管理员**<br>`admin` | **全站最高特权**：<br>1. 用户与成员管理维护；<br>2. 动态分配与调整角色；<br>3. 租户 Token 预算充值扩容；<br>4. 执行所有沙箱代码与通关评测。 |
| **🛠️ AI 架构研发负责人** | `dev_lead` | `Dev@2026` | **企业核心智算中心**<br>`tenant_enterprise_core` | **研发工程师**<br>`developer` | **研发日常权限**：<br>1. 调试沙箱代码；<br>2. 提交自动化通关验证；<br>3. 无法调整团队角色与租户账单。 |
| **🔬 算法科学家** | `researcher` | `Lab@2026` | **创新算法实验室**<br>`tenant_algorithm_lab` | **研发工程师**<br>`developer` | **独立隔离租户**：<br>1. 归属于算法隔离租户；<br>2. 专属 50 万 Token 月度预算配额；<br>3. 独立的执行历史与沙箱命名空间。 |
| **👁️ 只读受限访客** | `guest` | `Guest@2026` | **体验试用租户**<br>`tenant_guest_sandbox` | **只读观察者**<br>`viewer` | **受限体验/安全拦截**：<br>1. 仅允许只读浏览指导书与报表；<br>2. **禁止执行代码与评测** (触发 403 拦截)；<br>3. 预算极低，用于演练熔断保护。 |

---

## 🏢 二、 多租户配额与治理规则设定

系统针对不同组织和部门分配了独立的资源配额与限流门禁：

| 租户标识 (Tenant ID) | 租户显示名称 | 月度 Token 预算 | 滑动窗口限流 (QPS) | 当前状态 | 业务定位说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tenant_enterprise_core` | **企业核心智算中心** | **2,000,000 Tokens** | 50 次/秒 | 🟢 健康运行 | 主租户，高并发与高配额，支撑企业级大模型与 Agent 重度开发 |
| `tenant_algorithm_lab` | **创新算法实验室** | **500,000 Tokens** | 20 次/秒 | 🟢 健康运行 | 算法创新团队，独立资源池，隔离日常实验与生产流量 |
| `tenant_guest_sandbox` | **体验试用租户** | **10,000 Tokens** | 2 次/秒 | 🔴 逼近熔断 | 外部体验与测试租户，已消耗 9,850 Tokens，极易触发安全熔断机制 |

---

## 🛡️ 三、 角色权限矩阵定义 (RBAC Matrix)

企业统一访问控制采用最小特权原则，对算力调用与数据变更进行严格门禁管理：

| 权限标识 (Permission Key) | 功能描述 | 超级管理员 (`admin`) | 研发工程师 (`developer`) | 只读访客 (`viewer`) |
| :--- | :--- | :---: | :---: | :---: |
| `sandbox:run` | 在安全隔离沙箱中执行 Python 代码 | ✅ 允许 | ✅ 允许 | ❌ 阻断 (403 Forbidden) |
| `sandbox:verify` | 提交关卡自动化单元测试与通关判定 | ✅ 允许 | ✅ 允许 | ❌ 阻断 (403 Forbidden) |
| `model:infer` | 触发大模型多模态推理与 Agent 循环 | ✅ 允许 | ✅ 允许 | ❌ 阻断 (403 Forbidden) |
| `budget:write` | 调整/充值租户当月 Token 预算上限 | ✅ 允许 | ❌ 阻断 (403 Forbidden) | ❌ 阻断 (403 Forbidden) |
| `user:manage` | 新增团队用户、分配角色与权限维护 | ✅ 允许 | ❌ 阻断 (403 Forbidden) | ❌ 阻断 (403 Forbidden) |

---

## 🚀 四、 快速登录与 API 调用指引

### 1. Web 界面一键登录/切换
1. 在浏览器打开 **[http://localhost:6000](http://localhost:6000)**；
2. 点击顶部导航栏右侧的 **【身份徽章】**（如 `👑 超管: admin`）；
3. 弹出的窗口中内置了 **一键快捷登录按钮**，点击对应身份即可秒级免密切换。

### 2. 命令行 (curl) 鉴权与 API 调用示例

#### ① 登录获取企业 JWT 令牌
```bash
curl -X POST http://localhost:6001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "AgentForge@2026"
  }'
```
*响应结果将包含合规的 Base64URL 签名 JWT Token、租户配额与权限清单。*

#### ② 携带凭证执行代码沙箱（超管身份，正常运行并扣减 Token）
```bash
curl -X POST http://localhost:6001/api/v1/sandbox/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{"code": "print(1 + 1)"}'
```

#### ③ 访客身份尝试运行（将触发安全拦截）
```bash
# 使用 guest 账号登录获取 Token 后请求：
curl -X POST http://localhost:6001/api/v1/sandbox/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <GUEST_TOKEN>" \
  -d '{"code": "print(1 + 1)"}'
```
*响应结果：`{"status": "error", "error": "🔒 [权限拦截 403 Forbidden]：当前登录身份为【只读访客 (Viewer)】，受企业数据安全策略限制，禁止在沙箱中执行任意动态代码。"}`*

---

## ⚙️ 五、 角色维护与用户管理操作

使用 `admin` 账号登录后，可点击顶部导航栏的 **【🛡️ 权限治理】** 按钮：
1. **添加新成员**：输入新用户的用户名、初始密码与角色（如分配为 `developer`），一键纳入当前租户；
2. **动态调整角色**：在用户列表中，随时可将某个用户从 `viewer` 升级为 `developer` 或 `admin`，修改后该用户立即享有对应权限；
3. **预算配额充值**：在【Token 预算调优与充值】选项卡中，可将当前租户的预算从 200 万扩大到 500 万，解救因算力超标被熔断的业务租户；
4. **用户使用行为与审计流水追踪**：在【用户使用与审计流水】选项卡中，管理员可实时穿透跟进各租户成员的系统操作全貌，包括登录时间、沙箱调试频次、通关判定结果、Token 算力消耗及 403 越权拦截记录。

---

## 🔍 六、 强制鉴权守卫与全生命周期使用跟进

为避免未登录状态下进入系统导致无法跟进每个用户的系统使用情况，平台引入了企业级强管控：
1. **未登录绝对阻断 (Auth Guard)**：未携带合法 Token 的用户打开 `http://localhost:6002/` 或 `6000/` 时，强制呈现企业高质感暗黑登录大屏，杜绝匿名进入；
2. **全生命周期审计中枢 (Audit Trail Engine)**：后端每一次登录、沙箱运行、用量扣减、安全拦截与熔断，均自动记录带有时戳、租户标识、消耗 Token 的审计流水，支持按租户/用户过滤与回溯。

---

## 🛠️ 七、 服务日常运维与启动指令

如需重启平台服务或进行冒烟自检，可在项目根目录下执行：

```bash
# 1. 一键启动前后端全栈多租户服务 (后端 6001 / 前端 6000 / 桥接 6002)
./scripts/start_platform.sh

# 2. 运行全局 12 项全栈冒烟、权限拦截与审计追踪自动化回归测试
python3 tests/test_e2e_smoke.py

# 3. 运行官方 CLI 诊断体检
python3 scripts/agentforge_cli.py doctor
```
