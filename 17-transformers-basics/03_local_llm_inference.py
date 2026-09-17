from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch

def main():
    print("=== 第三课：本地开源模型推理 ===")
    # 为了能在你的 Mac 上快速跑通，这里选用极小参数量的模型 (0.5B，约 1GB 内存)
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"正在加载本地 LLM: {model_id} \n(初次运行会自动下载几百MB的权重)...")
    
    # 判断是否为 Mac M系列芯片，如果是则使用 MPS 加速，否则用 CPU
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"当前计算设备: {device.upper()}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    # Mac M 系列无需 bitsandbytes 量化，直接使用 float16 加载可提升速度
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device)
    
    # 创建文本生成流水线
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
    
    # 业务场景：绝密数据提取，不能调用外部API
    prompt_text = "客户张三的证件是110105199001011234，请告诉我他的证件号码是多少？"
    
    # 按照 Qwen2.5 的对话模板构建输入
    messages = [
        {"role": "system", "content": "你是一个严谨的信息提取助手，请准确回答用户的问题。"},
        {"role": "user", "content": prompt_text}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    print(f"\n[用户提问]: {prompt_text}")
    print("正在本地推理生成回答，请稍候...\n")
    
    # 执行生成
    result = pipe(
        prompt, 
        max_new_tokens=50, 
        do_sample=True, 
        temperature=0.1
    )
    
    # 提取生成的回复部分
    generated_text = result[0]['generated_text']
    response = generated_text[len(prompt):]
    
    print("[模型回复]:")
    print(response.strip())

if __name__ == "__main__":
    main()
