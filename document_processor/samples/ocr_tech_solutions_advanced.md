# OCR 开源框架全景深度对比与高阶代码实战 (PaddleOCR vs EasyOCR)

通过最新技术雷达探测，目前市面上表现最为卓越的开源 OCR 框架为 **PaddleOCR**（综合 benchmark 极高，适用于企业级复杂版面）与 **EasyOCR**（超强多语言支持，API 极简）。本文将对它们的底层实现机制与高阶定制化代码进行深度剖析。

## 1. PaddleOCR 进阶与架构实现

PaddleOCR 的底层架构是标准的三段式 OCR 管道（Pipeline）：
1. **Text Detection (文本检测)**：负责框出文字的区域（返回多边形或矩形框）。
2. **Text Classification (方向分类，可选)**：负责判断检测到的文字块是否倒置，进行 180 度翻转。
3. **Text Recognition (文本识别)**：对截取出的正向文字区域进行序列识别。

### 1.1 使用最新版 PP-OCRv5 Server 级大模型
在算力充足的服务器端，我们可以放弃轻量级移动端模型，直接加载精度极高的 `PP-OCRv5_server` 级模型：

```python
from paddleocr import PaddleOCR

# 初始化服务器级大模型（相比轻量模型精度更高，适合复杂排版）
ocr_engine = PaddleOCR(
    text_detection_model_name="PP-OCRv5_server_det",
    text_recognition_model_name="PP-OCRv5_server_rec",
    use_doc_orientation_classify=False, # 根据需求可关闭全局版面方向分类以提速
    use_doc_unwarping=False,
)

result = ocr_engine.predict("invoice.png")
res = result[0]
dt_polys = res["dt_polys"]  # 获得所有文本框的多边形坐标
rec_texts = res["rec_texts"] # 获得识别出的字符串
```

### 1.2 基于 ONNX Runtime 的极致提速
在某些非 Python 原生环境下，或者需要极致推理速度时，可以将检测模型导出为 ONNX 格式并用 C++ 引擎运行：

```python
from paddleocr import TextDetection

# 切换底层推理引擎为 onnxruntime
model = TextDetection(engine="onnxruntime")
output = model.predict("general_ocr_001.png", batch_size=1)
for res in output:
    res.print()
```

---

## 2. EasyOCR 进阶与高阶接口拆解

EasyOCR 底层依赖 PyTorch 与 CRNN，支持超过 80 种语言。其最大特色是 API 设计极其人性化，非常适合快速集成。

### 2.1 高阶参数与格式控制
除了简单的 `readtext`，EasyOCR 还提供了强大的输入支持与精细化参数控制（段落合并、白名单约束等）：

```python
import easyocr
import cv2

# 初始化中英双语识别器，强制使用 CPU (gpu=False)
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

# 支持直接传入 OpenCV BGR 格式的 numpy 数组
img = cv2.imread('receipt.png')

# 1. 段落模式：自动将靠近的离散文字块合并为一个大段落
paragraphs = reader.readtext(img, paragraph=True, detail=1)

# 2. JSON 格式输出
results_json = reader.readtext(img, output_format='json')

# 3. 动态防干扰（Allowlist / Blocklist）
# 比如识别发票上的金额时，只允许输出数字，避免把污渍识别为标点
digits_only = reader.readtext(img, allowlist='0123456789.')
# 比如识别昵称时，屏蔽掉系统不支持的特殊符号
no_symbols = reader.readtext(img, blocklist='!@#$%^&*')
```

### 2.2 检测 (Detect) 与识别 (Recognize) 的解耦
在复杂业务中，我们往往需要手动干预文本框的位置（例如只识别特定区域里的印章内容）。EasyOCR 完美支持将检测与识别两步解耦：

**步骤 A：仅进行文本检测 (Text Detection)**
```python
horizontal_list_agg, free_list_agg = reader.detect(
    img,
    text_threshold=0.7,   # 接受一个区域作为文本的置信度阈值
    low_text=0.4,         # 字符区域分数下限
    link_threshold=0.4,   # 邻近字符区域合并的阈值
    min_size=20           # 过滤掉小于 20px 的噪点文字框
)
# 获得轴对齐的矩形框列表
horizontal_list = horizontal_list_agg[0] 
```

**步骤 B：对指定框进行文本识别 (Text Recognition)**
在识别阶段，可以指定更为强悍的解码器（如集成了语言模型的 Beam Search）：
```python
img_grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

results = reader.recognize(
    img_grey,
    horizontal_list=horizontal_list,
    free_list=[],
    decoder='beamsearch',   # 默认是 greedy (贪心策略)，改为波束搜索可提升长句正确率
    beamWidth=5,            # 波束宽度
    detail=1
)

for (bbox, text, confidence) in results:
    print(f"提取结果: {text} (置信度: {confidence:.3f})")
```

## 3. 技术选型总结
- 如果您的业务是**证件、发票、表格、复杂版面解析**，且追求极致的精度上限与移动端部署，**PaddleOCR** 的 PP-OCRv4/v5 体系是毫无疑问的首选。
- 如果您的业务需求是**快速识别多国冷门语言文字**、或者需要高度定制化的解耦接口与极简的 Python API 集成，**EasyOCR** 是更敏捷的选择。
