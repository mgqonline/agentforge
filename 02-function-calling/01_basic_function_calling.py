import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, BaseMessage
from langchain_core.tools import tool

# 加载环境变量
load_dotenv()

# 1. 定义一个简单的工具
@tool
def get_weather(location: str):
    """获取指定地点的当前天气。"""
    # 模拟 API 返回
    if "长沙" in location:
        return "长沙天气晴，气温 35度。"
    elif "深圳" in location:
        return "深圳有小雨，气温 27度。"
    else:
        return f"{location}的天气数据暂未找到。"

# 自定义 ChatOpenAI 类以支持 DeepSeek 的 reasoning_content (彻底修复回传问题)
class DeepSeekChatOpenAI(ChatOpenAI):
    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        for i, res in enumerate(result.generations):
            if hasattr(response.choices[i].message, "reasoning_content"):
                # 将思维内容存入 additional_kwargs
                res.message.additional_kwargs["reasoning_content"] = response.choices[i].message.reasoning_content
        return result

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # 拦截 payload 构建过程
        # 获取原始 payload
        from langchain_openai.chat_models.base import _convert_message_to_dict
        
        # 重新构建 messages 列表，确保 reasoning_content 被注入到字典中
        payload_messages = []
        for msg in messages:
            msg_dict = _convert_message_to_dict(msg)
            if isinstance(msg, AIMessage) and "reasoning_content" in msg.additional_kwargs:
                msg_dict["reasoning_content"] = msg.additional_kwargs["reasoning_content"]
            payload_messages.append(msg_dict)
            
        # 这里的 hack 是：我们不能直接修改 _generate 的行为而不复制它的逻辑
        # 或者我们覆盖 _convert_message_to_dict (如果是实例方法)
        return super()._generate(messages, stop, run_manager, **kwargs)

    # 尝试覆盖这个方法，如果它是实例方法的话
    def _convert_message_to_dict(self, message: BaseMessage):
        msg_dict = super()._convert_message_to_dict(message)
        if isinstance(message, AIMessage) and "reasoning_content" in message.additional_kwargs:
            msg_dict["reasoning_content"] = message.additional_kwargs["reasoning_content"]
        return msg_dict

# 更加底层的修复方案：直接在调用前处理 messages
def fix_messages_for_deepseek(messages):
    """
    由于 LangChain 的 ChatOpenAI 在转换为 dict 时会丢失 reasoning_content，
    且 DeepSeek 要求必须传回。如果 LangChain 修复不便，我们可以尝试
    在 messages 层面做文章（虽然 AIMessage 不支持直接设置 reasoning_content 属性）。
    """
    pass

def run_function_calling_basics():
    print("--- Function Calling (函数调用) 基础练习 (DeepSeek 适配版) ---")
    
    # 2. 初始化模型并绑定工具
    model = DeepSeekChatOpenAI(model="deepseek-v4-flash", temperature=0)
    tools = [get_weather]
    model_with_tools = model.bind_tools(tools)

    # 3. 第一轮对话：模型决定调用工具
    query = "长沙今天天气怎么样？"
    print(f"\n用户提问: {query}")
    
    messages = [HumanMessage(content=query)]
    ai_msg = model_with_tools.invoke(messages)
    
    print("\n模型响应 (包含 tool_calls):")
    reasoning = ai_msg.additional_kwargs.get("reasoning_content", "")
    if reasoning:
        print(f"Thinking: {reasoning}")
    print(f"Content: {ai_msg.content}")
    print(f"Tool Calls: {ai_msg.tool_calls}")

    # 4. 模拟手动执行工具并返回结果给模型
    if ai_msg.tool_calls:
        messages.append(ai_msg)
        
        for tool_call in ai_msg.tool_calls:
            # 找到对应的工具并运行
            selected_tool = {"get_weather": get_weather}[tool_call["name"].lower()]
            tool_output = selected_tool.invoke(tool_call["args"])
            
            # 将工具结果包装成 ToolMessage
            messages.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=str(tool_output)
            ))
        
        # 5. 第二轮对话：模型根据工具结果生成最终回答
        print("\n将工具结果返回给模型...")
        # 如果自定义类依然不行，最后的绝招是使用原始 openai 库处理这一步
        try:
            final_response = model_with_tools.invoke(messages)
            print(f"\n最终回答: {final_response.content}")
        except Exception as e:
            if "reasoning_content" in str(e):
                print("\n[检测到 DeepSeek reasoning_content 兼容性问题，启动紧急修复方案...]")
                # 最后的绝招：手动调用 OpenAI 客户端
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
                
                # 手动构建消息列表
                raw_messages = []
                for m in messages:
                    if isinstance(m, HumanMessage):
                        raw_messages.append({"role": "user", "content": m.content})
                    elif isinstance(m, AIMessage):
                        msg_dict = {"role": "assistant", "content": m.content or ""}
                        if m.tool_calls:
                            msg_dict["tool_calls"] = [
                                {
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}
                                } for tc in m.tool_calls
                            ]
                        if "reasoning_content" in m.additional_kwargs:
                            msg_dict["reasoning_content"] = m.additional_kwargs["reasoning_content"]
                        raw_messages.append(msg_dict)
                    elif isinstance(m, ToolMessage):
                        raw_messages.append({
                            "role": "tool",
                            "tool_call_id": m.tool_call_id,
                            "content": m.content
                        })
                
                response = client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=raw_messages
                )
                print(f"\n最终回答 (通过 OpenAI SDK): {response.choices[0].message.content}")
            else:
                raise e

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here":
        print("错误: 请在 .env 文件中配置有效的 OPENAI_API_KEY")
    else:
        run_function_calling_basics()
