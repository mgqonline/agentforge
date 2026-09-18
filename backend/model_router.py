"""
AgentForge · 高可用大模型路由与多路故障熔断中枢 (LLM Circuit Breaker & Failover Router)
================================================================================
核心职责：
  1. 多线路主备倒换：配置 Primary（主）与 Multiple Fallbacks（备用），故障毫秒级自动切换；
  2. 智能熔断器 (Circuit Breaker)：遇到 429 (限流)、5xx (服务宕机)、Timeout 自动计入熔断指标，
     经历 CLOSED -> OPEN -> HALF_OPEN 自动自愈探测循环；
  3. 指数退避与抖动重试 (Exponential Backoff + Jitter)；
  4. 观测与诊断：向前端网关与运维看板实时汇报集群节点健康水位与热切换指标。
"""

import os
import time
import random
import asyncio
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
import openai

logger = logging.getLogger("agentforge.model_router")

class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # 正常通路
    OPEN = "OPEN"            # 熔断阻断 (主线路暂不可用，流量直切备用)
    HALF_OPEN = "HALF_OPEN"  # 半开探测 (允许试探请求，成功则恢复，失败再熔断)

class ProviderNode(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str
    model_name: str
    priority: int = 1  # 1 为主，2,3.. 为备用
    timeout_seconds: float = 30.0
    failure_threshold: int = 3       # 连续失败多少次触发 OPEN 熔断
    recovery_timeout: float = 30.0   # 熔断后冷却多久进入 HALF_OPEN 试探
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_fallovers: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: float = 0.0
    last_error_msg: str = ""

    def is_available(self) -> bool:
        """检查节点当前是否可用于流量分发"""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            now = time.time()
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"🔄 [ModelRouter] 线路 [{self.name}] 冷却时间已到，状态转入 HALF_OPEN 半开试探")
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self):
        """请求成功回调：重置连续失败计数，恢复 CLOSED 状态"""
        self.total_calls += 1
        self.consecutive_failures = 0
        if self.state != CircuitState.CLOSED:
            logger.info(f"✅ [ModelRouter] 线路 [{self.name}] 试探成功，熔断状态已完全恢复为 CLOSED 正常！")
            self.state = CircuitState.CLOSED

    def record_failure(self, error: Exception):
        """请求失败回调：累计计数并判断是否熔断"""
        self.total_calls += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        self.last_error_msg = str(error)

        if self.state == CircuitState.HALF_OPEN:
            # 半开试探失败，立即重新打回 OPEN
            self.state = CircuitState.OPEN
            logger.warning(f"⚠️ [ModelRouter] 线路 [{self.name}] 半开试探再次失败，重新进入 OPEN 熔断: {error}")
        elif self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"🚨 [ModelRouter 熔断告警] 线路 [{self.name}] 连续失败 {self.consecutive_failures} 次，"
                f"已触发 Circuit Breaker 熔断保护！冷却时间: {self.recovery_timeout}s"
            )

class ModelFailoverRouter:
    """
    企业级 LLM 故障转移与多主备路由中枢
    """
    def __init__(self, providers: Optional[List[ProviderNode]] = None):
        self.providers: List[ProviderNode] = providers or []
        if not self.providers:
            self._load_from_env()

    def _load_from_env(self):
        """从环境变量加载主线路与备用线路"""
        # 1. 主线路 (Primary)
        primary_key = os.getenv("OPENAI_API_KEY", "dummy")
        primary_base = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
        primary_model = os.getenv("MODEL_NAME", "deepseek-chat")
        primary_name = os.getenv("PRIMARY_PROVIDER_NAME", "DeepSeek 官方生产主干道")

        self.providers.append(
            ProviderNode(
                id="provider_primary",
                name=primary_name,
                base_url=primary_base,
                api_key=primary_key,
                model_name=primary_model,
                priority=1,
                timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "35.0")),
                failure_threshold=int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3")),
                recovery_timeout=float(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "30.0")),
            )
        )

        # 2. 备用线路 1 (Secondary: 如阿里云百炼 / 硅基流动 / 备用中转)
        fallback_key = os.getenv("FALLBACK_API_KEY")
        fallback_base = os.getenv("FALLBACK_API_BASE")
        fallback_model = os.getenv("FALLBACK_MODEL_NAME", "deepseek-chat")
        fallback_name = os.getenv("FALLBACK_PROVIDER_NAME", "企业备用高可用线路 (阿里云百炼/硅基流动)")

        if fallback_key and fallback_base:
            self.providers.append(
                ProviderNode(
                    id="provider_fallback_1",
                    name=fallback_name,
                    base_url=fallback_base,
                    api_key=fallback_key,
                    model_name=fallback_model,
                    priority=2,
                    timeout_seconds=float(os.getenv("FALLBACK_TIMEOUT_SECONDS", "30.0")),
                    failure_threshold=int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3")),
                    recovery_timeout=float(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "30.0")),
                )
            )
        else:
            # 默认注册一个自动镜像备用节点（用于测试或脱机兜底）
            self.providers.append(
                ProviderNode(
                    id="provider_fallback_mock",
                    name="备用冗余热备线路 (Auto-Fallback Node)",
                    base_url=primary_base,
                    api_key=primary_key,
                    model_name=primary_model,
                    priority=2,
                    timeout_seconds=30.0,
                    failure_threshold=3,
                    recovery_timeout=30.0,
                )
            )

    def add_provider(self, provider: ProviderNode):
        self.providers.append(provider)
        self.providers.sort(key=lambda p: p.priority)

    def get_available_providers(self) -> List[ProviderNode]:
        """按优先级升序返回当前所有可用节点"""
        available = [p for p in self.providers if p.is_available()]
        available.sort(key=lambda p: p.priority)
        return available

    def get_cluster_status(self) -> Dict[str, Any]:
        """返回当前模型集群各节点的监控指标与健康诊断"""
        now = time.time()
        nodes_status = []
        for p in self.providers:
            remaining_cooldown = max(0.0, round(p.recovery_timeout - (now - p.last_failure_time), 1)) if p.state == CircuitState.OPEN else 0.0
            nodes_status.append({
                "id": p.id,
                "name": p.name,
                "priority": p.priority,
                "model_name": p.model_name,
                "base_url": p.base_url.split("//")[-1].split("/")[0] if "//" in p.base_url else p.base_url, # 隐藏内网完整路径
                "state": p.state.value,
                "is_available": p.is_available(),
                "consecutive_failures": p.consecutive_failures,
                "total_calls": p.total_calls,
                "total_failures": p.total_failures,
                "total_fallovers": p.total_fallovers,
                "remaining_cooldown_seconds": remaining_cooldown,
                "last_error": p.last_error_msg,
            })
        
        has_primary = any(n["priority"] == 1 and n["state"] == CircuitState.CLOSED.value for n in nodes_status)
        cluster_health = "healthy" if has_primary else ("degraded" if any(n["is_available"] for n in nodes_status) else "critical")

        return {
            "cluster_health": cluster_health,
            "total_nodes": len(self.providers),
            "active_available_nodes": len(self.get_available_providers()),
            "nodes": nodes_status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        temperature: float = 0.7,
        max_retries_per_node: int = 2,
        **kwargs
    ) -> Any:
        """
        高可用流式/非流式模型调用，集成自动重试、熔断与跨节点无缝倒换
        """
        available_nodes = self.get_available_providers()
        if not available_nodes:
            raise RuntimeError(
                "🚨 [ModelRouter] 所有模型接入线路均处于熔断或不可用状态！请检查 API 密钥、网络或联系运维管理员。"
            )

        last_exception = None
        for node_idx, node in enumerate(available_nodes):
            client = openai.AsyncOpenAI(
                api_key=node.api_key,
                base_url=node.base_url,
                timeout=node.timeout_seconds
            )

            # 针对当前节点执行重试逻辑 (指数退避)
            for attempt in range(max_retries_per_node + 1):
                try:
                    if node_idx > 0:
                        logger.warning(
                            f"🔀 [ModelRouter 故障倒换触发] 流量自动切换至备用节点: [{node.name}], 正在执行请求..."
                        )
                        node.total_fallovers += 1

                    res = await client.chat.completions.create(
                        model=node.model_name,
                        messages=messages,
                        stream=stream,
                        temperature=temperature,
                        **kwargs
                    )
                    # 成功执行，上报节点成功并退出
                    node.record_success()
                    return res

                except Exception as exc:
                    last_exception = exc
                    is_rate_limit = "429" in str(exc) or "rate limit" in str(exc).lower()
                    is_server_err = any(code in str(exc) for code in ["500", "502", "503", "504"])
                    is_timeout = isinstance(exc, (asyncio.TimeoutError, openai.APITimeoutError))

                    logger.warning(
                        f"⚠️ [ModelRouter] 节点 [{node.name}] 调用失败 (尝试 {attempt + 1}/{max_retries_per_node + 1}): {exc}"
                    )

                    # 如果还有重试机会且属于可重试异常（429、5xx、超时）
                    if attempt < max_retries_per_node and (is_rate_limit or is_server_err or is_timeout):
                        backoff = (2 ** attempt) * 0.5 + random.uniform(0.1, 0.3)
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        # 当前节点多次重试仍失败，记录节点失败（可能触发熔断）并继续倒换下一个节点
                        node.record_failure(exc)
                        break

        # 如果所有可用节点尝试完依然失败，则向上抛出最后捕获的异常
        raise RuntimeError(
            f"🚨 [ModelRouter] 多路全线路调用皆失败，最后捕获异常: {last_exception}"
        ) from last_exception

# 全局单例路由器
model_failover_router = ModelFailoverRouter()
