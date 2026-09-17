import numpy as np
from langchain_community.embeddings import HuggingFaceEmbeddings

def cosine_similarity(v1, v2):
    """
    手动实现余弦相似度计算
    公式: (v1 · v2) / (||v1|| * ||v2||)
    """
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot_product / (norm_v1 * norm_v2)

def run_similarity_demo():
    # 1. 初始化本地 Embedding 模型
    # 使用一个小巧但高效的模型: sentence-transformers/all-MiniLM-L6-v2
    print("正在加载 Embedding 模型...")
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model = HuggingFaceEmbeddings(model_name=model_name)

    # 2. 准备测试句子
    sentences = [
        "我喜欢人工智能",           # 基准句子
        "我热爱 AI 技术",           # 语义高度相关
        "今天天气真的很不错",        # 语义完全无关
        "我不喜欢人工智能"           # 语义相反，但关键词重合度高
    ]

    # 3. 将句子转换为向量 (Embeddings)
    print("正在将句子转换为向量...")
    embeddings = [model.embed_query(s) for s in sentences]
    
    # 4. 打印向量维度
    print(f"向量维度: {len(embeddings[0])}")
    print(f"示例向量 (前 5 位): {embeddings[0][:5]}...\n")

    # 5. 计算相似度
    base_embedding = embeddings[0]
    print(f"对比基准: '{sentences[0]}'\n")
    
    for i in range(1, len(sentences)):
        sim = cosine_similarity(base_embedding, embeddings[i])
        print(f"与 '{sentences[i]}' 的相似度: {sim:.4f}")
        
        if sim > 0.8:
            print("  -> 结论: 语义高度一致")
        elif sim > 0.4:
            print("  -> 结论: 关键词相关，但语义可能有偏离")
        else:
            print("  -> 结论: 几乎没有任何关系")
        print()

if __name__ == "__main__":
    run_similarity_demo()
