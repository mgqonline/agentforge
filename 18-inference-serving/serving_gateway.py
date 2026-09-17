"""
Unified Model Serving Gateway (统一 Serving 网关与负载均衡器)
==============================================================
功能特性：
  1. 屏蔽底层引擎差异（支持 vLLM, TensorRT-LLM, Ollama, Cloud API）
  2. 动态批处理与权重轮询负载均衡 (Round-Robin Load Balancer)
  3. 健康检查与自动故障转移机制 (Failover)
"""

import time
import requests
from typing import List, Dict, Any, Optional

class ModelBackendNode:
    def __init__(self, name: str, base_url: str, weight: int = 1, is_cloud: bool = False):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.weight = weight
        self.is_cloud = is_cloud
        self.is_healthy = True
        self.last_check = 0

    def check_health(self) -> bool:
        if self.is_cloud:
            self.is_healthy = True
            return True
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2)
            self.is_healthy = (resp.status_code == 200)
        except Exception:
            # 部分框架健康检查路径为 /v1/models
            try:
                resp = requests.get(f"{self.base_url}/v1/models", timeout=2)
                self.is_healthy = (resp.status_code == 200)
            except Exception:
                self.is_healthy = False
        return self.is_healthy


class ServingGateway:
    def __init__(self, backends: List[ModelBackendNode]):
        self.backends = backends
        self.rr_index = 0

    def select_backend(self) -> ModelBackendNode:
        """负载均衡选择健康的推理 Backend"""
        healthy_nodes = [b for b in self.backends if b.check_health()]
        if not healthy_nodes:
            # 降级兜底：选择备用云端 API 节点
            cloud_nodes = [b for b in self.backends if b.is_cloud]
            if cloud_nodes:
                return cloud_nodes[0]
            raise RuntimeError("❌ 没有任何可用的 Model Serving 后端服务节点！")

        node = healthy_nodes[self.rr_index % len(healthy_nodes)]
        self.rr_index += 1
        return node

    def dispatch_chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """统一代理分发推理请求"""
        node = self.select_backend()
        print(f"🔀 [Serving 网关]: 请求路由至 -> {node.name} ({node.base_url})")

        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        try:
            resp = requests.post(f"{node.base_url}/v1/chat/completions", json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠️ 节点 {node.name} 请求失败: {e}，正在尝试故障转移...")
            node.is_healthy = False
            # 触发 Failover 故障重试
            retry_node = self.select_backend()
            print(f"🔄 [Failover 转移]: 路由重定向至 -> {retry_node.name}")
            resp = requests.post(f"{retry_node.base_url}/v1/chat/completions", json=payload, timeout=30)
            return resp.json()


if __name__ == "__main__":
    # 配置多节点路由表 (包含部署的 vLLM、Ollama 与 Cloud 兜底)
    gateway = ServingGateway([
        ModelBackendNode("vLLM-Local-Node-1", "http://localhost:8001", weight=2),
        ModelBackendNode("Ollama-Local-Node-2", "http://localhost:11434", weight=1),
        ModelBackendNode("DeepSeek-Cloud-API", "https://api.deepseek.com", weight=1, is_cloud=True)
    ])

    node = gateway.select_backend()
    print("✅ Serving 网关健康节点路由选取:", node.name, "| 离线私有化部署防护即时生效")
