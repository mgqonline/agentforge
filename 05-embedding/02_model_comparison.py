import os
import numpy as np
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

# 加载环境变量
load_dotenv()

def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot_product / (norm_v1 * norm_v2)

def run_model_comparison():
    # 准备测试对
    test_cases = [
        ("我喜欢人工智能", "我不喜欢人工智能"), # 逻辑否定测试
        ("北京是中国的首都", "中国的首都是北京"), # 句式变换测试
        ("苹果很好吃", "我刚买了一部苹果手机")  # 歧义词测试
    ]

    # 1. 定义要对比的模型
    models = {
        "MiniLM (轻量级/英文为主)": HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
        "Text2Vec-Chinese (中文优化)": HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese"),
        # 如果配置了 OpenAI Key 且 API 支持 Embedding
        # "OpenAI (text-embedding-3-small)": OpenAIEmbeddings(model="text-embedding-3-small")
    }

    print("=== Embedding 模型能力对比实验 ===\n")

    for model_name, model in models.items():
        print(f"--- 正在测试模型: {model_name} ---")
        try:
            for s1, s2 in test_cases:
                v1 = model.embed_query(s1)
                v2 = model.embed_query(s2)
                sim = cosine_similarity(v1, v2)
                print(f"句子 A: {s1}")
                print(f"句子 B: {s2}")
                print(f"相似度: {sim:.4f}")
                
                # 特殊逻辑判断：对于“喜欢”和“不喜欢”，理想模型应该给出较低的相似度
                if s1 == "我喜欢人工智能" and s2 == "我不喜欢人工智能":
                    if sim > 0.9:
                        print("  [结论]: 该模型无法识别否定词逻辑 (严重混淆)")
                    elif sim > 0.7:
                        print("  [结论]: 该模型对否定词逻辑识别较弱")
                    else:
                        print("  [结论]: 该模型能较好地区分否定逻辑")
                print()
        except Exception as e:
            print(f"测试出错: {e}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_model_comparison()
