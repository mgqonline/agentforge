import os
from huggingface_hub import hf_hub_download

# 使用国内镜像加速下载
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("🚀 正在通过 HuggingFace 国内镜像站拉取 YOLOv8 面部识别权重...")
try:
    # Bingsu/adetailer 仓库中包含了原版的 yolov8n-face.pt
    downloaded_path = hf_hub_download(
        repo_id="Bingsu/adetailer",
        filename="face_yolov8n.pt",
        repo_type="model"
    )
    
    # 移动到 DeepFace 期望的目录
    home = os.path.expanduser("~")
    target_dir = os.path.join(home, ".deepface", "weights")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, "yolov8n-face.pt")
    
    import shutil
    shutil.copy(downloaded_path, target_path)
    print(f"✅ 下载并部署成功！权重已安装至: {target_path}")
    print("👉 现在请重启你的 FastAPI 服务。")
    
except Exception as e:
    print(f"❌ 下载失败: {e}")
