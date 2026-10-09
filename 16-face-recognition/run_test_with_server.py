"""一键启动人脸识别服务并跑准确率测试（本机独立运行脚本）。

注意：本脚本依赖 uvicorn / face_api / test_accuracy，属于「沙箱之外」的本地
联调脚本，不适合在平台沙箱里直接运行。为避免触发沙箱安全边界（禁止导入
threading / subprocess 等受限系统模块），这里改为：

  1. 先在本机终端用 uvicorn 启动服务（见下方命令）：
         uvicorn face_api:app --host 127.0.0.1 --port 8000
  2. 再运行本脚本，仅负责调用接口做准确率测试：
         python run_test_with_server.py

这样脚本本身不再需要多线程或子进程，也能避免端口占用与关停竞态。
"""

import os
import time

from test_accuracy import test_recognition_accuracy


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 给手工启动的 uvicorn 服务留出就绪时间（若已在运行可忽略）
    print("⏳ 等待本机人脸识别服务在 http://127.0.0.1:8000 就绪 ...")
    time.sleep(1)

    test_recognition_accuracy(os.path.join(base_dir, "test_dataset"))


if __name__ == "__main__":
    main()