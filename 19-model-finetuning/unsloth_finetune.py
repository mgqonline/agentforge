# 注意：Unsloth 目前强依赖 NVIDIA GPU (CUDA) 环境，无法在 macOS (Apple Silicon) 本地运行。
# 推荐将此脚本放在 Google Colab (免费 T4 GPU) 或企业的 Linux 服务器上执行。

# 依赖安装提示 (若在 Colab 运行，请先执行以下命令):
# !pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
# !pip install --no-deps "xformers<0.0.27" "trl<0.9.0" peft accelerate bitsandbytes

from unsloth import FastLanguageModel
import torch
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# 1. 基础配置
max_seq_length = 2048 # Unsloth 内部做了优化，支持无限长上下文缩放
dtype = None # 为 None 则自动检测。由于我们需要快速训练，通常会采用 4-bit 量化
load_in_4bit = True # 使用 4-bit 量化大幅节省显存

# 2. 极速加载模型与 Tokenizer
print("🚀 正在通过 Unsloth 加载模型...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit", # 使用预先量化好的模型，下载更快
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# 3. 注入 LoRA 适配器 (注入可训练的微调层)
print("🔗 正在注入 LoRA 适配器...")
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # LoRA 秩，一般设为 8, 16, 32, 64 等
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0, # 不使用 dropout (Unsloth 对其有专属底层优化，设为 0 速度最快)
    bias = "none",
    use_gradient_checkpointing = "unsloth", # 极限显存节省优化
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)

# 4. 准备训练数据
print("📚 正在加载并格式化数据集...")
# 这里我们假设你将之前生成的 train.jsonl 传到了运行该脚本的服务器上
# 如果你使用自己的数据，只需修改这里的路径
dataset = load_dataset("json", data_files="train.jsonl", split="train")

def formatting_prompts_func(examples):
    # 根据之前 generate_dataset.py 的格式
    texts = examples["text"]
    return { "text" : texts }

dataset = dataset.map(formatting_prompts_func, batched = True)

# 5. 配置 SFT (Supervised Fine-Tuning) Trainer
print("⚙️ 配置 SFTTrainer...")
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, # 如果数据都是短文本可以设为 False，长文本开启能加速训练
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # 仅为快速演示，训练 60 步
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# 6. 开始飞速炼丹！
print("🔥 开始训练！")
trainer_stats = trainer.train()

# 7. 保存微调后的权重
print("💾 正在保存模型 LoRA 权重到 'lora_model' 目录...")
model.save_pretrained("lora_model")
tokenizer.save_pretrained("lora_model")
print("✅ Unsloth 微调大功告成！")

# 若要在训练后马上测试推理，可使用以下代码：
"""
FastLanguageModel.for_inference(model)
inputs = tokenizer(
[
    "<|im_start|>user\n你们公司的核心价值观是什么？<|im_end|>\n<|im_start|>assistant\n"
], return_tensors = "pt").to("cuda")

outputs = model.generate(**inputs, max_new_tokens = 64, use_cache = True)
print(tokenizer.batch_decode(outputs))
"""
