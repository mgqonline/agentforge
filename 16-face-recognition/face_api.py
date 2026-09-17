import io
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from deepface import DeepFace

app = FastAPI(title="企业级人脸识别 API (YOLOv8 + ArcFace)")

# =====================================================================
# 企业级人脸识别的核心痛点：
# 1. 纯 YOLO 只能做"人脸检测(Face Detection)"，告诉你图里有个人脸框，但不知道他是谁。
# 2. 纯 ArcFace/Facenet 只能做"特征比对"，如果你传进去一张带有背景的全身照，它会直接瞎掉。
# 
# 完美解决方案 (工业界黄金标准)：
# Pipeline: YOLOv8 极其精准地裁出人脸区域 -> ArcFace 提取 512 维特征向量 -> 余弦相似度比对
# =====================================================================

# 生产环境中，你应该把员工的人脸向量存入 Milvus/FAISS 向量数据库。
# 这里为了快速落地演示，我们使用本地文件夹作为底库。
import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_face_db")

@app.post("/recognize")
async def recognize_face(file: UploadFile = File(...)):
    """
    接收一张图片，使用 YOLOv8 检测人脸，并使用 ArcFace 识别身份
    """
    try:
        # 1. 读取 HTTP 传来的图片字节流，并无损转为 OpenCV 格式
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="解析图片失败，请上传合法图像格式")

        # 2. 核心管线启动
        # detector_backend='yolov8' : 严格采用用户要求的 YOLO 模型作为前置定位器
        # model_name='ArcFace'      : 采用目前公开的准确率最高 (99.8%) 的人脸识别引擎
        dfs = DeepFace.find(
            img_path=img, 
            db_path=DB_PATH, 
            model_name="ArcFace",      
            detector_backend="yolov8n", 
            enforce_detection=True,    # 图中必须有人脸，否则拦截报错
            silent=True                # 关闭冗余日志
        )
        
        # 3. 结果研判
        if len(dfs) > 0 and len(dfs[0]) > 0:
            # 拿到数据库中匹配度最高的那个人
            best_match = dfs[0].iloc[0]
            identity = best_match['identity'] # 匹配到的底片路径 (即员工姓名)
            distance = best_match['distance'] # 特征空间距离
            
            # ArcFace 的阈值一般在 0.68 左右。距离越小，长得越像！
            if distance < 0.68:
                return JSONResponse(content={
                    "status": "success",
                    "match": True,
                    "person_name": identity.split('/')[-1].split('.')[0], # 简单提取名字
                    "distance": float(distance),
                    "confidence": f"{(1 - distance)*100:.2f}%"  # 转换为置信度百分比
                })
                
        # 走到这里说明 YOLO 检测到了脸，但数据库里查无此人
        return JSONResponse(content={
            "status": "success",
            "match": False,
            "message": "⚠️ YOLO 检测到人脸，但在底库中未找到匹配的身份 (陌生人)"
        })

    except ValueError as e:
        # DeepFace 在 enforce_detection=True 且 YOLO 未发现人脸时会抛出 ValueError
        return JSONResponse(status_code=400, content={"status": "error", "message": "❌ YOLO 未在图中检测到任何人体面部！"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    # 启动 HTTP 接口服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
