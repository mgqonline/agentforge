import threading
import time
import subprocess
import uvicorn
from face_api import app
from test_accuracy import test_recognition_accuracy

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

# 在子线程启动服务器
t = threading.Thread(target=start_server, daemon=True)
t.start()

# 等待服务器启动
time.sleep(5)

import os
# 开始测试
base_dir = os.path.dirname(os.path.abspath(__file__))
test_recognition_accuracy(os.path.join(base_dir, "test_dataset"))
