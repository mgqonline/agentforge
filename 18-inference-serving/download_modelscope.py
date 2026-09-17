from modelscope import snapshot_download

print("🚀 正在从 ModelScope 下载 Qwen2.5-0.5B-Instruct...")
model_dir = snapshot_download('qwen/Qwen2.5-0.5B-Instruct')
print(f"✅ 下载完成！模型路径为: {model_dir}")
print(f"👉 请使用以下命令启动服务：\npython -m mlx_lm.server --model {model_dir} --port 8000")
