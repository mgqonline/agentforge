# IndexFlatL2 是 Faiss 中的一种索引类型，使用 L2 距离（欧氏距离）进行向量搜索。
# 它适用于小规模数据集，因为它会将所有向量存储在内存中，并且搜索时需要计算所有向量之间的距离。
'''
FAISS 详细讲解
什么是 FAISS
FAISS（Facebook AI Similarity Search）是 Meta 开源的高效向量相似度搜索库，
专门解决"在海量高维向量中快速找到最相似的几个"这个问题。
'''
import faiss
import numpy as np

d = 128  # 向量维度
index = faiss.IndexFlatL2(d)

# 添加向量
vectors = np.random.random((10000, d)).astype('float32')
index.add(vectors)

# 搜索最近的 5 个
query = np.random.random((1, d)).astype('float32')
distances, indices = index.search(query, k=5)
print("最近的 5 个向量索引:", indices)
print("对应的距离:", distances)