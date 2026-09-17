FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装底层系统依赖（OpenCV、编译辅助与健康检查工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖（利用 Docker 缓存层）
COPY backend/requirements.docker.txt /app/backend/requirements.docker.txt
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /app/backend/requirements.docker.txt

# 复制必要业务代码
COPY backend /app/backend
COPY examples /app/examples
COPY document_processor /app/document_processor

# 预创建缓存目录与数据存储目录
RUN mkdir -p /app/backend/chroma_db /app/backend/models /app/backend/logs

WORKDIR /app/backend

EXPOSE 6001

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:6001/docs || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6001", "--ws-max-size", "104857600"]
