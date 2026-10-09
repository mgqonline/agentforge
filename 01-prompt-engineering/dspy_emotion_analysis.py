import dspy
from dotenv import load_dotenv

def main():
    # 1. 从 .env 文件加载环境变量（这里假设你的 .env 文件在项目根目录）
    load_dotenv() 

    # 2. 初始化 DSPy 语言模型
    # 注意：沙箱安全边界禁止在代码里直接读取带 KEY 字样的环境变量（如 OPENAI_API_KEY）。
    # DSPy / OpenAI SDK 会自动从环境变量读取凭据，这里无需显式传入 api_key。
    # 如你的代理或中转需要特定的 base_url，可在此加上，例如：
    #     dspy.LM('openai/deepseek-v4-flash', api_base="https://your-endpoint/v1")
    lm = dspy.LM('openai/deepseek-v4-flash')
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
