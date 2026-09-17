from transformers import AutoTokenizer

def main():
    print("=== 第一课：Tokenizer 基础 ===")
    # 使用 Qwen2.5 的分词器（模型无需下载完整权重，只需下载 tokenizer 词表）
    tokenizer_id = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"正在加载分词器: {tokenizer_id} ...")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
    
    text = "合同违约金一般怎么算？如果甲方逾期付款，乙方有权要求按日万分之五支付违约金。"
    print(f"\n[原始文本]: {text}")
    
    # 1. 编码：将文本转换为 Token ID
    tokens = tokenizer.encode(text)
    print(f"\n[Token ID 序列]: {tokens}")
    print(f"[Token 数量]: {len(tokens)} 个 token")
    
    # 2. 截断演示：假设 API 限制最多输入 10 个 token
    print("\n[演示安全截断 (Max Length = 10)]:")
    safe_inputs = tokenizer(
        text, 
        max_length=10, 
        truncation=True, 
        return_tensors="pt"
    )
    safe_text = tokenizer.decode(safe_inputs["input_ids"][0], skip_special_tokens=True)
    print(f"[截断后的文本]: {safe_text}")

if __name__ == "__main__":
    main()
