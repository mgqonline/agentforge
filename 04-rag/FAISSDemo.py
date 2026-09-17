# FAISS 示例
'''
FAISS 详细讲解
什么是 FAISS
FAISS（Facebook AI Similarity Search）是 Meta 开源的高效向量相似度搜索库，
专门解决"在海量高维向量中快速找到最相似的几个"这个问题。
'''
from sentence_transformers import SentenceTransformer
import faiss

model = SentenceTransformer('BAAI/bge-m3')
corpus = [
    "冷链运输 温度 监控 异常",
    "货物 配送 延误 处理",
    "生鲜 蔬菜 保鲜 仓储",
]
embeddings = model.encode(corpus)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

query_vec = model.encode(["低温货品运输出问题了"])
distances, indices = index.search(query_vec, k=2)
# 能找到"冷链运输温度监控异常" ✓ （即使没有共同词）
print("查询结果：")
for idx, dist in zip(indices[0], distances[0]):
    print(f"文档索引: {idx}, 距离: {dist:.4f}, 内容: {corpus[idx]}")