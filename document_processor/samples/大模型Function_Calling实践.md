# 大模型 Function Calling 实践

## 1. 概念解析
Function Calling（函数调用/工具调用）是大语言模型的一项高级能力。它允许模型不仅仅输出自然语言文本，还能输出结构化的指令（如 JSON 格式的函数参数）。
通过这一机制，大模型可以控制外部系统、查询实时数据或执行特定的本地代码。

## 2. 工作原理
1. **定义工具**：开发者定义一组可用的工具集合，并详细描述每个工具的名称、用途和所需参数（通常使用 JSON Schema）。
2. **提交给模型**：将用户请求与工具定义一并发送给大模型。
3. **模型决策**：大模型判断是否需要调用工具来回答用户问题。如果需要，模型会生成一个要求调用特定工具的指令，并附带组装好的参数。
4. **执行工具**：开发者的后端系统接收到模型的工具调用指令后，在本地执行对应的 Python/Java/JS 函数，获取结果。
5. **回传结果**：将工具执行的返回结果作为上下文再次发给模型。
6. **最终回答**：模型综合工具返回的数据，生成最终的自然语言回答给用户。

## 3. Python 脚本演示代码
以下是一段使用 Python 编写的精简演示脚本：

```python
import json

def get_weather(location):
    """一个本地函数：获取指定城市的天气"""
    if "北京" in location:
        return "晴，25摄氏度"
    return "未知天气"

# 定义模型可见的工具结构
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取特定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "城市名称，如：北京"}
            },
            "required": ["location"]
        }
    }
}]

# 模拟大模型返回了调用指令
ai_response = {
    "tool_calls": [
        {
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "北京"}'
            }
        }
    ]
}

# 解析并执行
for tc in ai_response["tool_calls"]:
    func_name = tc["function"]["name"]
    args = json.loads(tc["function"]["arguments"])
    
    if func_name == "get_weather":
        result = get_weather(**args)
        print(f"工具执行结果: {result}")
```

## 总结
掌握 Function Calling 是开发 Agent 智能体的第一步。它是实现自动化的核心基础。
