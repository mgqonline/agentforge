def simulate_ragas_scoring():
    """
    模拟 RAGAS 评估逻辑的演示脚本。
    RAGAS 评估需要四种数据：
    1. Question: 用户提的问题
    2. Contexts: 检索到的文档片段（列表）
    3. Answer: AI 生成的回答
    4. Ground Truth: 标准答案（人工标注的正确答案）
    """

    print("=== RAGAS 评估指标模拟演示 ===\n")

    # --- 案例数据 ---
    data = {
        "question": "RAG 的核心组件有哪些？",
        "contexts": [
            "文档加载器和切分器是 RAG 的基础。", 
            "Chroma 是一个常用的向量库。"
        ],
        "answer": "RAG 的组件包括文档加载器、切分器和向量库。它是通过检索来增强生成的。",
        "ground_truth": "RAG 的核心组件有：文档加载器、文本切分器、向量存储和嵌入模型。"
    }

    print(f"❓ 问题: {data['question']}")
    print(f"📖 检索到的上下文: {data['contexts']}")
    print(f"🤖 AI 的回答: {data['answer']}")
    print(f"🎯 标准答案 (Ground Truth): {data['ground_truth']}\n")

    print("-" * 30)

    # --- 指标 1: Faithfulness (忠实度) ---
    # 逻辑：回答中的每一个观点，是否都能在上下文（Contexts）中找到根据？
    # AI 回答了：加载器、切分器、向量库。
    # 上下文包含：加载器、切分器、向量库。
    print("1. Faithfulness (忠实度) [分值: 高]")
    print("   原因: AI 说出的组件在检索到的片段中都有提到。没有瞎编。")

    # --- 指标 2: Answer Relevance (答案相关度) ---
    # 逻辑：回答是否直接解决了用户的问题？
    print("2. Answer Relevance (相关度) [分值: 高]")
    print("   原因: 回答紧扣“组件”这个主题，没有扯到无关话题。")

    # --- 指标 3: Context Precision (上下文精度) ---
    # 逻辑：检索到的片段里，有多少是真正对回答有帮助的？
    # 第 1 条有用，第 2 条描述 Chroma（向量库的一种）也有用。
    print("3. Context Precision (精度) [分值: 极高]")
    print("   原因: 搜到的两条资料都和 RAG 组件直接相关。")

    # --- 指标 4: Context Recall (上下文召回率) ---
    # 逻辑：标准答案（Ground Truth）里提到的点，上下文（Contexts）里都搜出来了吗？
    # 标准答案提到了：加载器、切分器、向量存储、嵌入模型。
    # 上下文漏掉了：“嵌入模型”。
    print("4. Context Recall (召回率) [分值: 中低]")
    print("   原因: 数据库里（或检索器）漏掉了‘嵌入模型’这一核心信息。这是检索环节的失败。")

    print("\n" + "=" * 50)
    print("💡 结论：")
    print("这个 RAG 系统的主要问题在于 [检索环节]。虽然模型回答得很诚实（忠实度高），")
    print("但因为它没搜到完整的资料（召回率低），所以回答是不完整的。")
    print("建议：优化 Embedding 模型或调整检索参数（如增加 K 值）。")

if __name__ == "__main__":
    simulate_ragas_scoring()
