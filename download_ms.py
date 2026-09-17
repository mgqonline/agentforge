from modelscope.hub.snapshot_download import snapshot_download
model_dir = snapshot_download('qwen/Qwen2.5-VL-7B-Instruct', local_dir='models/Qwen2.5-VL-7B-Instruct')
print("Download success to", model_dir)
