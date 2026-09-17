import os
import dspy
from dotenv import load_dotenv

def main():
    # 1. 从 .env 文件加载环境变量（这里假设你的 .env 文件在项目根目录）
    load_dotenv() 

    # 2. 获取 API_KEY
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("未找到 OPENAI_API_KEY，请检查 .env 文件是否配置正确。")

    # 3. 初始化 DSPy 语言模型
    # 这里使用的是 gpt-4o-mini，如果你的代理或中转需要特定的 base_url，
    # 也可以在这里加上，例如：dspy.LM('openai/gpt-4o-mini', api_key=api_key, api_base="...")
    lm = dspy.LM('openai/deepseek-v4-flash', api_key=api_key)
    dspy.settings.configure(lm=lm)

    # 4. 定义 Signature
    class EmotionAnalysis(dspy.Signature):
        """分析给定文本的情感倾向。"""
        sentence: str = dspy.InputField(desc="需要分析的句子")
        emotion: str = dspy.OutputField(desc="情感结果，必须是 positive, negative 或 neutral 之一")

    # 5. 使用带思维链的生成模块
    analyzer = dspy.ChainOfThought(EmotionAnalysis)
    
    # 6. 测试用例
    test_sentence = "DSPy 把我从调 Prompt 的地狱中拯救了出来，太棒了！"
    print(f"正在分析句子: '{test_sentence}'\n")
    
    result = analyzer(sentence=test_sentence)

    # 7. 打印结果
    # 注意：新版 DSPy 的 ChainOfThought 推导过程属性名改为了 reasoning
    rationale = getattr(result, 'reasoning', getattr(result, 'rationale', '未获取到推导过程'))
    print("🧠 思维链推导过程:", rationale) 
    print("✨ 最终情感结果:", result.emotion)
    print("\n🔍 完整输出对象:", result)

if __name__ == "__main__":
    main()
