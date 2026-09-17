import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from huggingface_hub import snapshot_download

snapshot_download(repo_id="Qwen/Qwen2.5-VL-7B-Instruct", local_dir="models/Qwen2.5-VL-7B-Instruct", local_dir_use_symlinks=False, resume_download=True)
