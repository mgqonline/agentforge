# OCR技术与解决方案全景指南

## 1. 什么是多模态 OCR 技术？
光学字符识别 (Optical Character Recognition, OCR) 旨在将图片、扫描件上的文字转换为可编辑的结构化文本。现代“多模态 OCR”不仅能识别纯文本，还能结合排版、印章、手写体、甚至图表和复杂的数学公式，将视觉信息转换为完整的文档结构。

## 2. 业界主流解决方案对比

### 2.1 Tesseract OCR (开源老牌)
- **优势**：免费开源，支持离线，语言包丰富。
- **劣势**：对复杂排版、手写体和自然场景文字（如路牌、带背景的图片）识别率较低。

### 2.2 PaddleOCR (当前开源标杆)
- **优势**：百度开源的飞桨方案。轻量级模型（PP-OCRv4）仅几兆，支持多语言，检测与识别精度极高，支持版面分析。
- **劣势**：需要配置 Python 环境，C++ 部署有一定门槛。

### 2.3 商业化云服务 API (阿里/腾讯/Google Vision)
- **优势**：接入极简，高并发，对特殊场景（如发票、身份证、银行卡）有专用的定制化模型。
- **劣势**：按调用次数收费，且涉及敏感数据出境风险（若是公有云）。

## 3. 具体代码编写案例：使用 PaddleOCR 提取图片文字

以下是一个完整的 Python 代码案例，展示如何使用 `PaddleOCR` 快速实现图文提取：

### 3.1 环境准备
在终端执行以下命令安装核心依赖（请确保环境中已安装 OpenCV）：
```bash
pip install paddlepaddle paddleocr
```

### 3.2 核心代码实现

新建脚本 `run_ocr.py`，代码如下：

```python
import os
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image

# 1. 初始化 OCR 引擎
# use_angle_cls=True 表示自动检测图片方向并进行旋转校正
# lang='ch' 表示支持中英文混合识别
ocr = PaddleOCR(use_angle_cls=True, lang='ch')

def process_image(img_path):
    print(f"正在处理图片: {img_path}")
    
    # 2. 执行 OCR 识别
    # 返回结果结构: [[[[[点1, 点2, 点3, 点4], ('识别出的文本', 置信度)]], ...]]
    result = ocr.ocr(img_path, cls=True)
    
    if not result or result[0] is None:
        print("未检测到任何文字")
        return
        
    extracted_text = []
    
    # 3. 遍历提取结果
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            # 提取文本内容和置信度
            text_content = line[1][0]
            confidence = line[1][1]
            
            extracted_text.append(text_content)
            print(f"识别文本: {text_content} | 置信度: {confidence:.4f}")
            
    # 将提取出的纯文本返回，可以直接丢进 RAG 系统
    return "\n".join(extracted_text)

if __name__ == "__main__":
    # 测试文件路径
    test_image_path = "./sample_invoice.jpg"
    
    if os.path.exists(test_image_path):
        full_text = process_image(test_image_path)
        print("\n--- 提取总结 ---")
        print(full_text)
    else:
        print(f"找不到测试图片: {test_image_path}，请自行准备一张包含文字的图片。")
```

### 3.3 进阶：如何将 OCR 接入到大模型的 RAG 引擎中？
在上述代码提取出纯文本后，您可以直接利用我们后端的 `DocumentProcessor`，将其包装为 `Document` 节点：
```python
from langchain_core.documents import Document

# OCR 提取得到的文本
raw_text = process_image("user_upload.png")

# 包装并进行向量化
doc = Document(page_content=raw_text, metadata={"source": "user_upload.png", "type": "ocr_image"})

# 随后调用 vectorstore.add_documents([doc]) 即可入库！
```
这种混合了【图文解析】与【向量检索】的架构，是目前业界处理 PDF 和影印文档的最强解决方案！
