import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from model_router import ModelFailoverRouter, ProviderNode, CircuitState

@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions():
    """测试熔断状态机：CLOSED -> OPEN -> HALF_OPEN -> CLOSED"""
    node = ProviderNode(
        id="test_node",
        name="测试主干节点",
        base_url="http://fake.api",
        api_key="fake_key",
        model_name="fake_model",
        failure_threshold=2,
        recovery_timeout=0.2  # 0.2s 快速测试冷却
    )

    assert node.state == CircuitState.CLOSED
    assert node.is_available() is True

    # 第一次失败，尚未达到阈值 2
    node.record_failure(RuntimeError("429 Too Many Requests"))
    assert node.state == CircuitState.CLOSED
    assert node.consecutive_failures == 1

    # 第二次失败，达到阈值，触发 OPEN 熔断
    node.record_failure(RuntimeError("429 Too Many Requests"))
    assert node.state == CircuitState.OPEN
    assert node.is_available() is False

    # 冷却前，节点不可用
    await asyncio.sleep(0.05)
    assert node.is_available() is False

    # 等待冷却时间过去，进入 HALF_OPEN
    await asyncio.sleep(0.2)
    assert node.is_available() is True
    assert node.state == CircuitState.HALF_OPEN

    # 在 HALF_OPEN 下如果请求成功，恢复为 CLOSED 并且清零失败计数
    node.record_success()
    assert node.state == CircuitState.CLOSED
    assert node.consecutive_failures == 0

@pytest.mark.asyncio
async def test_failover_to_fallback_node():
    """测试当主线路连续失败时，路由器透明倒换到备用线路并成功返回结果"""
    primary = ProviderNode(
        id="p1",
        name="主线路",
        base_url="http://primary.com",
        api_key="key1",
        model_name="deepseek-v3",
        priority=1,
        failure_threshold=1,
    )
    fallback = ProviderNode(
        id="p2",
        name="备用百炼线路",
        base_url="http://fallback.com",
        api_key="key2",
        model_name="qwen-max",
        priority=2,
    )

    router = ModelFailoverRouter(providers=[primary, fallback])

    # 模拟 primary 抛出 429 限流异常，fallback 成功返回模拟响应
    async def mock_primary_create(*args, **kwargs):
        raise RuntimeError("HTTP 429: Rate limit reached on primary provider")

    async def mock_fallback_create(*args, **kwargs):
        return {"choices": [{"message": {"content": "这是来自备用百炼线路的高可用回复"}}]}

    with patch("openai.AsyncOpenAI") as mock_client_cls:
        client_instance = AsyncMock()
        mock_client_cls.return_value = client_instance

        # 根据传入的 base_url 动态返回 mock 实现
        def get_client(api_key=None, base_url=None, timeout=None):
            c = AsyncMock()
            if "primary" in str(base_url):
                c.chat.completions.create.side_effect = mock_primary_create
            else:
                c.chat.completions.create.side_effect = mock_fallback_create
            return c

        mock_client_cls.side_effect = get_client

        response = await router.chat_completion(
            messages=[{"role": "user", "content": "你好"}],
            max_retries_per_node=0
        )

        assert response["choices"][0]["message"]["content"] == "这是来自备用百炼线路的高可用回复"
        # 主线路触发熔断
        assert primary.state == CircuitState.OPEN
        assert primary.total_failures >= 1
        # 备用线路成功
        assert fallback.state == CircuitState.CLOSED
        assert fallback.total_calls >= 1
        assert fallback.total_fallovers >= 1

def test_cluster_status_diagnostics():
    """测试多节点健康诊断与监控输出格式"""
    primary = ProviderNode(
        id="p1", name="主节点", base_url="https://api.deepseek.com/v1",
        api_key="k1", model_name="m1", priority=1
    )
    fallback = ProviderNode(
        id="p2", name="备用节点", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="k2", model_name="m2", priority=2
    )
    router = ModelFailoverRouter(providers=[primary, fallback])
    status = router.get_cluster_status()

    assert status["cluster_health"] == "healthy"
    assert status["total_nodes"] == 2
    assert len(status["nodes"]) == 2
    assert status["nodes"][0]["priority"] == 1
    assert "api.deepseek.com" in status["nodes"][0]["base_url"]
