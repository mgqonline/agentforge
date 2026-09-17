# Hugging Face Transformers 核心技术指南

## 1. 什么是 Transformers 库？
`transformers` 是由 Hugging Face 维护的开源 NLP/多模态库。它提供了数千个预训练大模型（包括 BERT、GPT、Llama、Qwen、BGE 等），只需几行代码即可完成模型的下载、加载、微调与推理部署。

## 2. 核心架构：Pipeline 与底层拆解

Transformers 库的设计核心分为三大块：
1. **Tokenizer（分词器）**：负责将文本字符串转化为模型可以理解的数字特征（Token IDs）。
2. **Model（模型体）**：根据 Token ID 输出隐层状态或预测概率（如 `AutoModelForCausalLM` 用于生成式文本，`AutoModelForSequenceClassification` 用于文本分类）。
3. **Pipeline（流水线）**：将 Tokenizer 和 Model 封装为一个极简接口，屏蔽底层张量运算细节，适合开箱即用的快速推理。

## 3. 具体代码编写案例：生成式语言模型推理

以下是一个完整 Python 案例，展示如何使用 `transformers` 库加载大型语言模型并进行文本生成推理。

### 3.1 环境准备
在终端执行以下命令安装核心依赖（由于涉及张量运算，通常需要配合 PyTorch 使用）：
```bash
pip install transformers torch accelerate
```

### 3.2 核心代码实现：手动调用 Tokenizer 与 Model

对于大语言模型（如 Qwen 或 Llama），手动干预分词器有助于进行定制化的 Prompt Engineering，推荐使用如下方式：

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 1. 设定模型路径 (可以是本地路径，也可以是 Hugging Face 上的仓库名)
model_name = "Qwen/Qwen1.5-7B-Chat"

print(f"正在加载 Tokenizer: {model_name}...")
# trust_remote_code=True 允许加载第三方定义的架构代码
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

print(f"正在加载 Model: {model_name}...")
# device_map="auto" 表示由 accelerate 库自动将模型层分配到可用的 GPU 显存或 CPU 内存中
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.float16, # 使用半精度以节省显存
    trust_remote_code=True
)

def generate_answer(user_prompt):
    # 2. 构造对话模板
    messages = [
        {"role": "system", "content": "你是一个非常有用的AI助手。"},
        {"role": "user", "content": user_prompt}
    ]
    
    # 3. 将对话模板转化为模型需要的输入格式 (Prompt String)
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # 4. 文本编码 (转化为 Tensor)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    # 5. 模型推理生成 (自回归生成)
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9
    )
    
    # 由于生成的结果里包含了输入的 Prompt，需要将其裁剪掉
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    # 6. 解码 (将 Tensor 转化回人类可读文本)
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response

if __name__ == "__main__":
    prompt = "请简单解释一下 Transformer 模型的自注意力机制。"
    print(f"User: {prompt}")
    answer = generate_answer(prompt)
    print(f"Assistant: {answer}")
```

### 3.4 与现有架构结合 (RAG 检索引擎)
我们在 `rag_engine.py` 中正是使用了 transformers 生态（通过 `sentence-transformers` 或 `Langchain HuggingFaceEmbeddings` 封装）加载了 `BAAI/bge-m3` 模型，通过底层的张量池化（Pooling）操作，将整个文档段落转化为了一个 1024 维度的浮点数向量，从而实现了语义级的相似度匹配。
