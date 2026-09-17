import math

#   对于向量 A 和向量 B，余弦相似度的公式是：
#                              A·B
#     Cosine Similarity = ─────────────
#                         ||A|| × ||B||

#   • 分子（点积 / Dot Product）：把两个向量对应位置的数字相乘，然后全部加起来。
#   • 分母（向量长度的乘积）：向量 A 的长度乘以向量 B 的长度。

#   手动算一次刚才的 A  [2,3]  和 B  [4,6] ：

#   1. 分子（点积）：(2 × 4) + (3 × 6) = 8 + 18 = 26
#   2. 向量 A 的长度：√(2² + 3²) = √(13)
#   3. 向量 B 的长度：√(4² + 6²) = √(52)
#   4. 分母：√(13) × √(52) = √(676) = 26
#   5. 最终余弦相似度：26/26 = 1.0 (完美相似！)
# 假设这两个就是大模型输出的向量（这里简化为 3 维，实际上大模型是 512 或更长的维度）
vector_a = [2.0, 3.0, 1.0]
vector_b = [4.0, 6.0, 2.0]

def calculate_cosine_similarity(a, b):
    # 1. 算分子：对应位置相乘，再求和
    dot_product = sum(a[i] * b[i] for i in range(len(a)))

    # 2. 算分母：分别算各自的平方和开根号，再相乘
    magnitude_a = math.sqrt(sum(x ** 2 for x in a))
    magnitude_b = math.sqrt(sum(x ** 2 for x in b))

    # 3. 相除得出结果
    return dot_product / (magnitude_a * magnitude_b)

# 测试计算
result = calculate_cosine_similarity(vector_a, vector_b)
print(f"余弦相似度是: {result}")
# 因为 vector_b 正好是 vector_a 每一项乘 2，方向完全一致，所以输出将是 1.0