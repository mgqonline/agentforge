from transformers import AutoModel, AutoTokenizer
import torch

def main():
    print("=== 第二课：本地 Embedding 词向量 ===")
    model_name = "BAAI/bge-small-zh-v1.5"
    print(f"正在加载 Embedding 模型: {model_name}\n(初次运行会自动下载，约 100MB+)...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    
    sentences = [
        "合同违约金怎么算？", 
        "劳动法规定的辞退赔偿标准是什么？",
        "如果甲方违约，应该赔偿多少钱？"
    ]
    
    print("\n正在计算以下句子的特征向量：")
    for i, s in enumerate(sentences):
        print(f"[{i}] {s}")
        
    # 1. 分词与转换为张量
    inputs = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
    
    # 2. 模型推理提取向量
    with torch.no_grad():
        outputs = model(**inputs)
        # 取 [CLS] token 的向量作为整个句子的语义表示
        sentence_embeddings = outputs[0][:, 0]
        
    # 3. 标准化处理（用于计算余弦相似度进行 RAG 检索）
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    
    print(f"\n[成功] 生成的特征向量维度: {sentence_embeddings.shape} （3句话，每句话384维）")
    
    # 4. 简单验证余弦相似度
    # 句子0和句子2都是关于合同违约的，相似度应该更高
    sim_0_1 = torch.nn.functional.cosine_similarity(sentence_embeddings[0].unsqueeze(0), sentence_embeddings[1].unsqueeze(0))
    sim_0_2 = torch.nn.functional.cosine_similarity(sentence_embeddings[0].unsqueeze(0), sentence_embeddings[2].unsqueeze(0))
    
    print("\n[相似度计算结果]:")
    print(f"句[0] VS 句[1] -> {sim_0_1.item():.4f} (语义不相关)")
    print(f"句[0] VS 句[2] -> {sim_0_2.item():.4f} (语义高度相关)")

if __name__ == "__main__":
    main()
