import os
import sys

# ⚠️ 必须在所有 import 之前设置环境变量！
# 针对国内企业内网或强 DPI 防火墙导致的 HuggingFace SSL 阻断问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 既然本地已经缓存了该模型，我们直接开启完全离线模式，彻底切断所有网络请求！
os.environ["HF_HUB_OFFLINE"] = "1"

# 提示：此脚本依赖 mlx-lm，请确保提前执行了 `pip install mlx-lm`
try:
    from mlx_lm import load, generate
except ImportError:
    print("❌ 缺少 MLX 依赖。请运行: pip install mlx-lm")
    sys.exit(1)

# ==========================================
# 拓维信息 - 边缘端 (Edge AI) 本地推理示例
# ==========================================

# 采用本地已下载好的 Qwen2.5 模型
MODEL_REPO = "Qwen/Qwen2.5-0.5B-Instruct"

print(f"🔄 正在拓维信息AI应用开发中心的边缘设备上加载模型: {MODEL_REPO} ...\n(首次运行会自动从 HuggingFace 下载模型文件，请保持网络畅通)")

try:
    # load() 会自动将模型加载到 Apple Silicon 的统一内存架构 (UMA) 中，速度极快
    model, tokenizer = load(MODEL_REPO)
    print("✅ 模型加载成功！\n")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    sys.exit(1)

# 构建测试问题，融入业务上下文
prompt_text = "请简要介绍一下边缘计算 (Edge AI) 技术如何帮助像拓维信息这样的科技企业在工业制造领域提升效率？"

# 套用 Chat 模板
messages = [{"role": "user", "content": prompt_text}]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

print(f"👤 工程师提问:\n{prompt_text}\n")
print("🤖 本地边缘大模型思考中...\n")

# generate 触发本地推理
response = generate(
    model, 
    tokenizer, 
    prompt=prompt, 
    verbose=True,   # 开启 verbose 会在控制台打印生成的 Token 速率 (tok/sec)
    max_tokens=200
)

print("\n\n==========================================")
print("✅ 边缘计算推理完成！")
print("如你所见，全程没有向外部云端发送任何网络请求，数据 100% 留存本地。")
print("==========================================")
