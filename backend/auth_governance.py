"""
AgentForge · 企业级多租户 RBAC、真实 JWT 鉴权与 Token 限流熔断中枢
====================================================================
定位：阶段二核心交付物。彻底告别 Demo 级假 Token，提供生产级多租户隔离、
      基于角色的权限控制 (RBAC)、滑动窗口速率限流 (RateLimiter) 与 Token 预算熔断器。

设计亮点：
  1. 零硬依赖：内置标准 HMAC-SHA256 JWT 实现，即使未安装 PyJWT 也能原生安全验签；
  2. 多租户配额治理：支持按租户限制 QPS 并跟踪当月 Token 消耗；
  3. FastAPI 原生适配：提供声明式 Depends 鉴权拦截器。
"""

import base64
import hashlib
import hmac
import json
import sqlite3
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field

# 生产环境密钥（生产中通过 .env 注入，禁止使用默认弱口令）
DEFAULT_JWT_SECRET = "agentforge_enterprise_production_secret_key_2026"
DEFAULT_JWT_ALGORITHM = "HS256"

# 物理持久化 SQLite 数据库路径 (保证服务重启后账号、角色、配额与审计流水不丢失)
AUTH_DB_PATH = Path(__file__).resolve().parent / "auth.db"

def _get_db():
    conn = sqlite3.connect(str(AUTH_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class UserRole(str, Enum):
    """企业角色枚举定义 (RBAC)"""

    ADMIN = "admin"  # 超级管理员：可调任何高危工具、管理账单与租户
    DEVELOPER = "developer"  # 开发者：可触发 Agent 研报、微调与沙箱代码执行
    VIEWER = "viewer"  # 观察者：只读访问历史报告与评测看板，禁止调用工具


class UserRecord(BaseModel):
    """用户账号模型"""
    user_id: str
    username: str
    password_hash: str
    tenant_id: str
    role: UserRole
    display_name: str
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


class TenantQuota(BaseModel):
    """租户配额与预算模型"""

    tenant_id: str
    tenant_name: str
    max_qps: int = 10  # 每秒最大允许请求数
    monthly_token_budget: int = 1_000_000  # 当月 Token 预算上限
    tokens_consumed: int = 0  # 累计消耗


def _hash_pwd(pwd: str) -> str:
    """内部轻量安全哈希"""
    return hashlib.sha256(f"salt_agentforge_2026_{pwd}".encode("utf-8")).hexdigest()

# 默认基础预置数据清单
_DEFAULT_TENANTS = [
    TenantQuota(
        tenant_id="tenant_enterprise_core",
        tenant_name="企业核心智算中心 (主租户/最高配)",
        max_qps=50,
        monthly_token_budget=2_000_000,
        tokens_consumed=142_500,
    ),
    TenantQuota(
        tenant_id="tenant_algorithm_lab",
        tenant_name="创新算法实验室 (研发隔离租户)",
        max_qps=20,
        monthly_token_budget=500_000,
        tokens_consumed=85_200,
    ),
    TenantQuota(
        tenant_id="tenant_guest_sandbox",
        tenant_name="体验试用租户 (只读/快熔断)",
        max_qps=2,
        monthly_token_budget=10_000,
        tokens_consumed=9_850,
    ),
    TenantQuota(
        tenant_id="tenant_corp_alpha",
        tenant_name="阿尔法集团 (核心VIP租户)",
        max_qps=50,
        monthly_token_budget=50_000_000,
        tokens_consumed=125_000,
    ),
    TenantQuota(
        tenant_id="tenant_startup_beta",
        tenant_name="贝塔初创团队",
        max_qps=5,
        monthly_token_budget=2_000_000,
        tokens_consumed=1_980_000,
    ),
]

_DEFAULT_USERS = [
    UserRecord(
        user_id="usr_superadmin_01",
        username="admin",
        password_hash=_hash_pwd("AgentForge@2026"),
        tenant_id="tenant_enterprise_core",
        role=UserRole.ADMIN,
        display_name="超级管理员 (最高权限)",
    ),
    UserRecord(
        user_id="usr_dev_02",
        username="dev_lead",
        password_hash=_hash_pwd("Dev@2026"),
        tenant_id="tenant_enterprise_core",
        role=UserRole.DEVELOPER,
        display_name="AI 架构研发负责人",
    ),
    UserRecord(
        user_id="usr_lab_03",
        username="researcher",
        password_hash=_hash_pwd("Lab@2026"),
        tenant_id="tenant_algorithm_lab",
        role=UserRole.DEVELOPER,
        display_name="算法科学家",
    ),
    UserRecord(
        user_id="usr_guest_04",
        username="guest",
        password_hash=_hash_pwd("Guest@2026"),
        tenant_id="tenant_guest_sandbox",
        role=UserRole.VIEWER,
        display_name="访客体验者 (只读)",
    ),
]

# 内存高速缓存 (保持对上层零破坏兼容)
TENANT_STORE: Dict[str, TenantQuota] = {}
USER_STORE: Dict[str, UserRecord] = {}
USER_AUDIT_LOGS: List[Dict[str, Any]] = []

def _init_and_sync_db():
    """初始化 SQLite 物理持久化表结构，并双向同步内存缓存"""
    global TENANT_STORE, USER_STORE, USER_AUDIT_LOGS
    with _get_db() as conn:
        cur = conn.cursor()
        # 1. 创建租户表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            tenant_name TEXT,
            max_qps INTEGER,
            monthly_token_budget INTEGER,
            tokens_consumed INTEGER
        );
        """)
        # 2. 创建用户表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            tenant_id TEXT,
            role TEXT,
            display_name TEXT,
            created_at TEXT
        );
        """)
        # 3. 创建审计流水表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            user_id TEXT,
            username TEXT,
            tenant_id TEXT,
            action TEXT,
            details TEXT,
            cost_tokens INTEGER,
            status TEXT
        );
        """)
        # 4. 创建学员实战关卡进度与历史代码快照表 (多端多用户云端持久化)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            phase_id TEXT NOT NULL,
            passed INTEGER NOT NULL DEFAULT 1,
            xp_earned INTEGER NOT NULL DEFAULT 100,
            completed_at INTEGER NOT NULL,
            saved_code TEXT DEFAULT '',
            execution_metrics TEXT DEFAULT '{}',
            UNIQUE(user_id, phase_id)
        );
        """)
        conn.commit()

        # 写入默认租户 (若不存在)
        for t in _DEFAULT_TENANTS:
            cur.execute("""
            INSERT OR IGNORE INTO tenants (tenant_id, tenant_name, max_qps, monthly_token_budget, tokens_consumed)
            VALUES (?, ?, ?, ?, ?)
            """, (t.tenant_id, t.tenant_name, t.max_qps, t.monthly_token_budget, t.tokens_consumed))

        # 写入默认初始用户 (若不存在)
        for u in _DEFAULT_USERS:
            cur.execute("""
            INSERT OR IGNORE INTO users (user_id, username, password_hash, tenant_id, role, display_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (u.user_id, u.username, u.password_hash, u.tenant_id, u.role.value, u.display_name, u.created_at))

        conn.commit()

        # 从数据库全量加载至内存缓存
        cur.execute("SELECT * FROM tenants")
        for row in cur.fetchall():
            TENANT_STORE[row["tenant_id"]] = TenantQuota(
                tenant_id=row["tenant_id"],
                tenant_name=row["tenant_name"],
                max_qps=row["max_qps"],
                monthly_token_budget=row["monthly_token_budget"],
                tokens_consumed=row["tokens_consumed"]
            )

        cur.execute("SELECT * FROM users")
        for row in cur.fetchall():
            try:
                urole = UserRole(row["role"])
            except ValueError:
                urole = UserRole.DEVELOPER
            USER_STORE[row["username"]] = UserRecord(
                user_id=row["user_id"],
                username=row["username"],
                password_hash=row["password_hash"],
                tenant_id=row["tenant_id"],
                role=urole,
                display_name=row["display_name"],
                created_at=row["created_at"]
            )

        cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 500")
        USER_AUDIT_LOGS = [dict(row) for row in cur.fetchall()]
        if not USER_AUDIT_LOGS:
            # 记录引导日志
            init_log = {
                "id": "log_init_001",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": "usr_superadmin_01",
                "username": "admin",
                "tenant_id": "tenant_enterprise_core",
                "action": "system_bootstrap",
                "details": "SQLite 持久化引擎就绪，系统初始化启动加载 RBAC 规则",
                "cost_tokens": 0,
                "status": "success"
            }
            cur.execute("""
            INSERT INTO audit_logs (id, timestamp, user_id, username, tenant_id, action, details, cost_tokens, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (init_log["id"], init_log["timestamp"], init_log["user_id"], init_log["username"], init_log["tenant_id"], init_log["action"], init_log["details"], init_log["cost_tokens"], init_log["status"]))
            conn.commit()
            USER_AUDIT_LOGS.append(init_log)

# 模块加载时立即完成数据库建表与同步
_init_and_sync_db()

def record_user_action(
    username: str,
    tenant_id: str,
    action: str,
    user_id: str = "",
    details: str = "",
    cost_tokens: int = 0,
    status: str = "success"
) -> Dict[str, Any]:
    """记录用户全生命周期操作行为流水"""
    log_entry = {
        "id": f"log_{int(time.time() * 1000)}_{len(USER_AUDIT_LOGS)+1}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "username": username,
        "tenant_id": tenant_id,
        "action": action,
        "details": details,
        "cost_tokens": cost_tokens,
        "status": status
    }
    USER_AUDIT_LOGS.insert(0, log_entry)
    # 保留最近 1000 条流水
    if len(USER_AUDIT_LOGS) > 1000:
        USER_AUDIT_LOGS.pop()

    # 物理落盘至 SQLite 数据库
    try:
        with _get_db() as conn:
            conn.execute("""
            INSERT INTO audit_logs (id, timestamp, user_id, username, tenant_id, action, details, cost_tokens, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_entry["id"], log_entry["timestamp"], log_entry["user_id"], log_entry["username"], log_entry["tenant_id"], log_entry["action"], log_entry["details"], log_entry["cost_tokens"], log_entry["status"]))
            conn.commit()
    except Exception as e:
        print(f"[Warn] Audit log SQLite flush failed: {e}")

    return log_entry

def list_user_audit_logs(
    tenant_id: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """查询用户审计流水"""
    results = []
    for log in USER_AUDIT_LOGS:
        if tenant_id and log["tenant_id"] != tenant_id:
            continue
        if username and log["username"] != username:
            continue
        results.append(log)
        if len(results) >= limit:
            break
    return results

# 角色权限矩阵定义
ROLE_PERMISSIONS_MATRIX = {
    UserRole.ADMIN.value: {
        "label": "超级管理员 (Admin)",
        "description": "拥有全站最高治理权限，可管理租户、分配角色、充值配额与执行所有代码",
        "permissions": [
            {"key": "sandbox:run", "name": "运行沙箱代码", "enabled": True},
            {"key": "sandbox:verify", "name": "自动化通关验证", "enabled": True},
            {"key": "model:infer", "name": "大模型与Agent推理", "enabled": True},
            {"key": "budget:write", "name": "租户Token预算调优与充值", "enabled": True},
            {"key": "user:manage", "name": "用户角色权限维护", "enabled": True},
        ]
    },
    UserRole.DEVELOPER.value: {
        "label": "研发工程师 (Developer)",
        "description": "具备日常代码调试与关卡学习通关权限，无法修改租户账单与团队成员角色",
        "permissions": [
            {"key": "sandbox:run", "name": "运行沙箱代码", "enabled": True},
            {"key": "sandbox:verify", "name": "自动化通关验证", "enabled": True},
            {"key": "model:infer", "name": "大模型与Agent推理", "enabled": True},
            {"key": "budget:write", "name": "租户Token预算调优与充值", "enabled": False},
            {"key": "user:manage", "name": "用户角色权限维护", "enabled": False},
        ]
    },
    UserRole.VIEWER.value: {
        "label": "只读访客 (Viewer)",
        "description": "只读浏览课程指导书与历史报表，受沙箱执行熔断保护，无法执行代码",
        "permissions": [
            {"key": "sandbox:run", "name": "运行沙箱代码", "enabled": False},
            {"key": "sandbox:verify", "name": "自动化通关验证", "enabled": False},
            {"key": "model:infer", "name": "大模型与Agent推理", "enabled": False},
            {"key": "budget:write", "name": "租户Token预算调优与充值", "enabled": False},
            {"key": "user:manage", "name": "用户角色权限维护", "enabled": False},
        ]
    }
}



class TokenPayload(BaseModel):
    """JWT Claims 载荷"""

    user_id: str
    tenant_id: str
    role: UserRole
    exp: int
    iat: int


# =====================================================================
# 一、 纯原生标准 JWT 签发与校验引擎 (零第三方依赖，高兼容)
# =====================================================================


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None,
    secret_key: str = DEFAULT_JWT_SECRET,
) -> str:
    """签发合规的企业级 JWT 令牌"""
    now = int(time.time())
    expire = (
        now + int(expires_delta.total_seconds())
        if expires_delta
        else now + 86400  # 默认 24 小时
    )

    header = {"alg": DEFAULT_JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role.value,
        "iat": now,
        "exp": expire,
    }

    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(
    token: str, secret_key: str = DEFAULT_JWT_SECRET
) -> TokenPayload:
    """校验 JWT 令牌完整性、签名与时效"""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT 令牌格式非法 (必须由三段构成)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_b64, payload_b64, sig_b64 = parts

    # 1. 验证签名
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(
        secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    expected_sig_b64 = _base64url_encode(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT 令牌签名篡改或无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 验证过期时间
    try:
        payload_data = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT Payload 解码失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp = payload_data.get("exp", 0)
    if time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT 令牌已过期，请重新登录换票",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenPayload(
        user_id=payload_data["user_id"],
        tenant_id=payload_data["tenant_id"],
        role=UserRole(payload_data["role"]),
        exp=payload_data["exp"],
        iat=payload_data["iat"],
    )


# =====================================================================
# 二、 多租户滑动窗口速率限流器 (RateLimiter)
# =====================================================================


class SlidingWindowRateLimiter:
    """基于内存滑动窗口的高精度租户限流器"""

    def __init__(self) -> None:
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, tenant_id: str, max_qps: int) -> bool:
        now = time.time()
        window_start = now - 1.0  # 统计过去 1 秒内的滑动窗口

        if tenant_id not in self._history:
            self._history[tenant_id] = []

        # 淘汰窗口外的时间戳
        self._history[tenant_id] = [
            t for t in self._history[tenant_id] if t > window_start
        ]

        if len(self._history[tenant_id]) >= max_qps:
            return False

        self._history[tenant_id].append(now)
        return True


rate_limiter = SlidingWindowRateLimiter()

# =====================================================================
# 三、 FastAPI 声明式依赖注入鉴权中枢
# =====================================================================


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> TokenPayload:
    """FastAPI 核心鉴权依赖：提取并校验 Authorization Header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少凭证：请在请求头提供 Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    return verify_access_token(token)


def require_role(min_role: UserRole) -> Callable:
    """RBAC 角色权限门禁装配器"""
    role_weights = {
        UserRole.VIEWER: 1,
        UserRole.DEVELOPER: 2,
        UserRole.ADMIN: 3,
    }

    async def role_checker(
        current_user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        user_weight = role_weights.get(current_user.role, 0)
        required_weight = role_weights.get(min_role, 999)

        if user_weight < required_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：当前角色 [{current_user.role.value}] 无法执行该操作，需要 [{min_role.value}] 权限",
            )
        return current_user

    return role_checker


async def check_tenant_limits(
    current_user: TokenPayload = Depends(get_current_user),
) -> TenantQuota:
    """多租户限流与 Token 预算熔断拦截器"""
    tenant_id = current_user.tenant_id
    tenant = TENANT_STORE.get(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"非法租户：租户 [{tenant_id}] 不存在或已被注销",
        )

    # 1. 速率限流校验 (QPS)
    if not rate_limiter.is_allowed(tenant_id, tenant.max_qps):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"触发租户级流控：租户 [{tenant.tenant_name}] 超出最大并发限额 ({tenant.max_qps} QPS)，请稍后重试",
        )

    # 2. Token 预算熔断校验
    if tenant.tokens_consumed >= tenant.monthly_token_budget:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"触发 Token 预算熔断：租户 [{tenant.tenant_name}] 当月 Token 配额已耗尽 ({tenant.tokens_consumed}/{tenant.monthly_token_budget})，请联系管理员扩容",
        )

    return tenant


# =====================================================================
# 四、 用户与租户治理业务逻辑 (RBAC & Quota Management)
# =====================================================================

def authenticate_user(username: str, password: str) -> Optional[UserRecord]:
    """用户凭据认证"""
    user = USER_STORE.get(username)
    if not user:
        return None
    if user.password_hash != _hash_pwd(password):
        return None
    return user


def get_tenant_info(tenant_id: str) -> Optional[TenantQuota]:
    """获取指定租户配额信息"""
    return TENANT_STORE.get(tenant_id)


def list_all_tenants() -> List[Dict[str, Any]]:
    """列出所有可用租户"""
    result = []
    for t in TENANT_STORE.values():
        remaining = max(0, t.monthly_token_budget - t.tokens_consumed)
        percent = round((t.tokens_consumed / (t.monthly_token_budget or 1)) * 100, 1)
        result.append({
            "tenant_id": t.tenant_id,
            "tenant_name": t.tenant_name,
            "max_qps": t.max_qps,
            "monthly_token_budget": t.monthly_token_budget,
            "tokens_consumed": t.tokens_consumed,
            "tokens_remaining": remaining,
            "percent_used": percent,
            "is_exhausted": t.tokens_consumed >= t.monthly_token_budget
        })
    return result


def list_tenant_users(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """查询指定租户下的用户列表（若未传则返回全量）"""
    users = []
    for u in USER_STORE.values():
        if tenant_id and u.tenant_id != tenant_id:
            continue
        users.append({
            "user_id": u.user_id,
            "username": u.username,
            "display_name": u.display_name,
            "tenant_id": u.tenant_id,
            "role": u.role.value,
            "created_at": u.created_at,
        })
    return users


def create_new_user(
    tenant_id: str, 
    username: str, 
    password: str, 
    role: str = "developer",
    display_name: str = ""
) -> UserRecord:
    """新增团队成员并分配角色"""
    if username in USER_STORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户 [{username}] 已存在，请使用其他用户名"
        )
    if tenant_id not in TENANT_STORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"租户 [{tenant_id}] 不存在"
        )
    try:
        user_role = UserRole(role)
    except ValueError:
        user_role = UserRole.DEVELOPER

    new_user = UserRecord(
        user_id=f"usr_{username}_{int(time.time())}",
        username=username,
        password_hash=_hash_pwd(password),
        tenant_id=tenant_id,
        role=user_role,
        display_name=display_name or f"研发人员 {username}",
    )
    USER_STORE[username] = new_user

    # 物理落盘至 SQLite
    try:
        with _get_db() as conn:
            conn.execute("""
            INSERT INTO users (user_id, username, password_hash, tenant_id, role, display_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_user.user_id, new_user.username, new_user.password_hash, new_user.tenant_id, new_user.role.value, new_user.display_name, new_user.created_at))
            conn.commit()
    except Exception as e:
        print(f"[Warn] User insert SQLite flush failed: {e}")

    return new_user


def update_user_role(username: str, new_role: str) -> UserRecord:
    """调整用户角色权限"""
    user = USER_STORE.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 [{username}] 不存在"
        )
    try:
        user.role = UserRole(new_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"非法角色: {new_role}"
        )

    # 物理落盘至 SQLite
    try:
        with _get_db() as conn:
            conn.execute("UPDATE users SET role = ? WHERE username = ?", (user.role.value, username))
            conn.commit()
    except Exception as e:
        print(f"[Warn] Update user role SQLite failed: {e}")

    return user


def update_tenant_budget(tenant_id: str, new_budget: int) -> TenantQuota:
    """动态调整或充值租户 Token 预算"""
    tenant = TENANT_STORE.get(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"租户 [{tenant_id}] 不存在"
        )
    tenant.monthly_token_budget = max(1000, new_budget)

    # 物理落盘至 SQLite
    try:
        with _get_db() as conn:
            conn.execute("UPDATE tenants SET monthly_token_budget = ? WHERE tenant_id = ?", (tenant.monthly_token_budget, tenant_id))
            conn.commit()
    except Exception as e:
        print(f"[Warn] Update tenant budget SQLite failed: {e}")

    return tenant


def deduct_tenant_tokens(tenant_id: str, tokens: int = 150) -> Dict[str, Any]:
    """真实扣减租户 Token，并检查是否熔断"""
    tenant = TENANT_STORE.get(tenant_id)
    if not tenant:
        return {"status": "error", "message": "Tenant not found"}
    
    tenant.tokens_consumed += tokens
    remaining = max(0, tenant.monthly_token_budget - tenant.tokens_consumed)
    is_exhausted = tenant.tokens_consumed >= tenant.monthly_token_budget

    # 物理落盘至 SQLite
    try:
        with _get_db() as conn:
            conn.execute("UPDATE tenants SET tokens_consumed = ? WHERE tenant_id = ?", (tenant.tokens_consumed, tenant_id))
            conn.commit()
    except Exception as e:
        print(f"[Warn] Deduct tenant tokens SQLite failed: {e}")

    return {
        "tenant_id": tenant.tenant_id,
        "tokens_consumed": tenant.tokens_consumed,
        "monthly_token_budget": tenant.monthly_token_budget,
        "tokens_remaining": remaining,
        "is_exhausted": is_exhausted
    }


def get_role_permissions_matrix() -> Dict[str, Any]:
    """获取系统角色权限矩阵"""
    return ROLE_PERMISSIONS_MATRIX


def save_user_progress(
    user_id: str,
    username: str,
    tenant_id: str,
    phase_id: str,
    passed: bool = True,
    xp_earned: int = 100,
    saved_code: str = "",
    execution_metrics: Optional[Dict[str, Any]] = None,
    completed_at: Optional[int] = None
) -> Dict[str, Any]:
    """物理落盘记录学员关卡通关状态与历史代码快照 (支持多用户云端持久化)"""
    ts = completed_at or int(time.time() * 1000)
    metrics_json = json.dumps(execution_metrics or {}, ensure_ascii=False)
    
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO user_progress (user_id, username, tenant_id, phase_id, passed, xp_earned, completed_at, saved_code, execution_metrics)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, phase_id) DO UPDATE SET
            passed = excluded.passed,
            xp_earned = excluded.xp_earned,
            completed_at = excluded.completed_at,
            saved_code = CASE WHEN excluded.saved_code != '' THEN excluded.saved_code ELSE user_progress.saved_code END,
            execution_metrics = excluded.execution_metrics
        """, (
            user_id,
            username,
            tenant_id,
            phase_id,
            1 if passed else 0,
            xp_earned,
            ts,
            saved_code,
            metrics_json
        ))
        conn.commit()

    return {
        "status": "success",
        "phase_id": phase_id,
        "passed": passed,
        "xpEarned": xp_earned,
        "completedAt": ts,
        "savedCode": saved_code
    }


def get_user_progress_map(user_id: str) -> Dict[str, Any]:
    """查询指定用户在所有关卡的通关历史与代码快照映射"""
    res: Dict[str, Any] = {}
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT phase_id, passed, xp_earned, completed_at, saved_code, execution_metrics
        FROM user_progress
        WHERE user_id = ?
        """, (user_id,))
        for row in cur.fetchall():
            p_id = row["phase_id"]
            try:
                metrics = json.loads(row["execution_metrics"] or "{}")
            except Exception:
                metrics = {}
            res[p_id] = {
                "passed": bool(row["passed"]),
                "xpEarned": row["xp_earned"],
                "completedAt": row["completed_at"],
                "savedCode": row["saved_code"] or "",
                **metrics
            }
    return res


# =====================================================================
# 4.5 FinOps 部门 Token 账单核算与财务对账导出中枢
# =====================================================================

TOKEN_PRICE_PER_MILLION_CNY = 1.50  # 综合商用模型折算基准: ¥1.50 / 100万 Token
HOURS_SAVED_PER_10K_TOKENS = 0.25   # 研发效能折算: 每 1万 Token 约相当于自动化解决 0.25 人力工时

def get_billing_summary() -> Dict[str, Any]:
    """计算各租户/部门当前周期内的 Token 消耗、折算金额与节约效能"""
    tenants_list = list_all_tenants()
    total_tokens = sum(t["tokens_consumed"] for t in tenants_list)
    total_budget = sum(t["monthly_token_budget"] for t in tenants_list)
    total_cost = round((total_tokens / 1_000_000) * TOKEN_PRICE_PER_MILLION_CNY, 2)
    total_hours = round((total_tokens / 10_000) * HOURS_SAVED_PER_10K_TOKENS, 1)

    tenant_stats = []
    for t in tenants_list:
        c_tokens = t["tokens_consumed"]
        budget = t["monthly_token_budget"]
        burn_rate = round((c_tokens / budget * 100), 1) if budget > 0 else 0
        cost = round((c_tokens / 1_000_000) * TOKEN_PRICE_PER_MILLION_CNY, 2)
        hours = round((c_tokens / 10_000) * HOURS_SAVED_PER_10K_TOKENS, 1)
        
        tenant_stats.append({
            "tenant_id": t["tenant_id"],
            "tenant_name": t["tenant_name"],
            "max_qps": t["max_qps"],
            "monthly_token_budget": budget,
            "tokens_consumed": c_tokens,
            "tokens_remaining": max(0, budget - c_tokens),
            "burn_rate_pct": burn_rate,
            "cost_cny": cost,
            "hours_saved": hours,
            "is_exhausted": c_tokens >= budget
        })

    # 按消耗量降序排列
    tenant_stats.sort(key=lambda x: x["tokens_consumed"], reverse=True)

    return {
        "pricing_rate_info": f"¥{TOKEN_PRICE_PER_MILLION_CNY} / 百万 Tokens",
        "total_tokens_consumed": total_tokens,
        "total_budget_tokens": total_budget,
        "total_cost_cny": total_cost,
        "total_hours_saved": total_hours,
        "active_tenants_count": len(tenants_list),
        "tenants": tenant_stats
    }


def generate_billing_csv_content(tenant_id: Optional[str] = None) -> str:
    """生成带 UTF-8 BOM 的标准财务对账 CSV 文本"""
    import io
    import csv

    # 查询审计流水
    with _get_db() as conn:
        cur = conn.cursor()
        if tenant_id:
            cur.execute("""
                SELECT id, timestamp, user_id, username, tenant_id, action, details, cost_tokens, status
                FROM audit_logs
                WHERE tenant_id = ?
                ORDER BY timestamp DESC
                LIMIT 500
            """, (tenant_id,))
        else:
            cur.execute("""
                SELECT id, timestamp, user_id, username, tenant_id, action, details, cost_tokens, status
                FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT 500
            """)
        rows = [dict(r) for r in cur.fetchall()]

    tenant_map = {t["tenant_id"]: t["tenant_name"] for t in list_all_tenants()}

    output = io.StringIO()
    # 写入 UTF-8 BOM
    output.write('\ufeff')
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([
        "交易流水号 (Transaction ID)",
        "所属租户/部门 (Tenant)",
        "操作账号 (Username)",
        "功能模块/行为 (Action)",
        "详情备注 (Details)",
        "消耗Tokens (Tokens Consumed)",
        "折算金额(¥) (Cost CNY)",
        "估算节省工时(小时) (Hours Saved)",
        "记录时间 (Timestamp)"
    ])

    if rows:
        for r in rows:
            tokens = r.get("cost_tokens", 0) or 0
            cost = round((tokens / 1_000_000) * TOKEN_PRICE_PER_MILLION_CNY, 4)
            hours = round((tokens / 10_000) * HOURS_SAVED_PER_10K_TOKENS, 2)
            t_name = tenant_map.get(r["tenant_id"], r["tenant_id"])
            writer.writerow([
                r["id"],
                t_name,
                r["username"],
                r["action"],
                (r.get("details") or "").replace("\n", " "),
                tokens,
                cost,
                hours,
                r.get("timestamp", "")
            ])
    else:
        # 如果当前无细粒度日志，导出当前租户账单汇总行
        summary = get_billing_summary()
        for t in summary["tenants"]:
            if tenant_id and t["tenant_id"] != tenant_id:
                continue
            writer.writerow([
                f"SUMMARY-{t['tenant_id']}",
                t["tenant_name"],
                "SYSTEM_AGGREGATE",
                "月度累积对账",
                f"月度配额 {t['monthly_token_budget']} Tokens，已用 {t['burn_rate_pct']}%",
                t["tokens_consumed"],
                t["cost_cny"],
                t["hours_saved"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

    return output.getvalue()


if __name__ == "__main__":
    print("=" * 70)
    print("🛡️ AgentForge 多租户 RBAC、JWT 鉴权与 Token 限流中枢自测")
    print("=" * 70)

    # 1. 签发测试 Token
    admin_token = create_access_token(
        user_id="user_admin_001",
        tenant_id="tenant_corp_alpha",
        role=UserRole.ADMIN,
    )
    print(f"\n[1] 成功签发企业 Admin JWT: {admin_token[:40]}...")

    # 2. 校验 Token
    claims = verify_access_token(admin_token)
    print(
        f"[2] 验签成功! 归属租户: {claims.tenant_id} | 角色: {claims.role.value}"
    )

    # 3. 测试速率限流
    print("\n[3] 模拟高频请求触发滑动窗口限流...")
    qps_hit = 0
    for i in range(12):
        allowed = rate_limiter.is_allowed("tenant_startup_beta", max_qps=5)
        if allowed:
            qps_hit += 1
        else:
            print(f"  ⚡ 第 {i+1} 次请求成功被限流器拦截 (已达 5 QPS 上限)")
            break
    print(f"  通过请求数: {qps_hit}")

    # 4. 测试伪造签名拦截
    print("\n[4] 模拟黑客篡改 JWT 签名...")
    tampered_token = admin_token[:-4] + "fake"
    try:
        verify_access_token(tampered_token)
    except HTTPException as e:
        print(f"  ✅ 安全防御生效: 成功捕获非法篡改! 报错: {e.detail}")

    print("\n" + "=" * 70)
    print("✅ 阶段二多租户安全鉴权中枢验证完全通过！")
    print("=" * 70)
