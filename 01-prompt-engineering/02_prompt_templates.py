from langchain_core.prompts import ChatPromptTemplate

def practice_templates():
    print("--- Prompt Template 练习 ---")
    
    # 定义模板
    template = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译专家，负责将用户输入的{source_lang}文本翻译成{target_lang}。"),
        ("human", "{text}"),
    ])
    
    # 填充变量
    prompt_value = template.format_messages(
        source_lang="中文",
        target_lang="英文",
        text="不积跬步，无以至千里。"
    )
    
    print("\n生成的消息列表:")
    for msg in prompt_value:
        print(f"[{msg.type}]: {msg.content}")

if __name__ == "__main__":
    practice_templates()
