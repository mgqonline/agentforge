# 文档解析器 (Document Processor) 技术总结

本项目实现了一个能够处理异构文档（PDF、Word、Excel）并自动进行分块（Chunking）提取元数据（Metadata）的生产级文档处理模块。它是 RAG 系统前端数据摄取（Data Ingestion）环节的核心基建。

## 1. 使用的核心技术栈

| 技术组件 | 选型 | 作用与优势 |
| :--- | :--- | :--- |
| **PDF 解析** | `PyMuPDF (fitz)` | 性能极高，文本抽取精准度好，能保留基础的页面结构信息，比传统 PyPDF2 速度快 10 倍以上。 |
| **Word 解析** | `python-docx` | 能够按段落提取纯文本，过滤掉无关的样式和二进制元数据，提取的文本自然连贯。 |
| **Excel 解析** | `pandas` + `openpyxl` + `tabulate` | 将二维数据表转化为大语言模型最易于理解的 **Markdown 表格 (Markdown Table)** 格式，极大降低了 LLM 读取表格数据的幻觉。 |
| **基础数据结构** | `Dict / List` | 将切割好的文本打包为 `{"content": "...", "metadata": {...}}` 格式，与市面上的向量数据库（如 ChromaDB/Pinecone）无缝对接。 |

## 2. 采用的开发方法与理念

1. **防御性编程与风险阻断 (Safe Data Processing)**：
   - 在开发和运行数据解析脚本前，强制接入了 `risk_checker.py` 对 Python 文件进行了静态扫描，确保文件读写不涉及系统核心目录、无网络外发泄露风险、无危险系统调用。
2. **面向对象与开闭原则 (OOP)**：
   - 采用单一主入口 `process_file()`，通过文件后缀进行策略路由（Strategy Routing）。后续如果需要增加 PPTX 解析，只需要在类中新增 `_process_pptx` 方法，无需修改原有调用逻辑。
3. **大模型友好的分块策略 (Chunking for LLM)**：
   - 将整篇文档切割为规定长度的片段（如默认 500/1000 字符），防止超出 LLM 上下文窗口限制，同时提高向量检索的细粒度。
   - 自动在切割的内容片段中注入原始元数据（如 `source`, `type`, `page`）。

## 3. 执行步骤与快速上手

### 步骤一：安装环境依赖
进入你的 Python 虚拟环境后，安装核心解析依赖：
```bash
pip install pymupdf python-docx pandas openpyxl tabulate
```

### 步骤二：生成测试数据 (可选)
如果需要测试，可以直接运行数据生成脚本，它会在 `samples/` 目录下生成 PDF、Word、Excel 测试文件：
```bash
python generate_samples.py
```

### 步骤三：在代码中调用解析器
将该解析器导入到你的 RAG 流水线中，一键解析各种异构文档：

```python
from doc_parser import DocumentProcessor

# 1. 初始化，设定分块字符数为 500
parser = DocumentProcessor(chunk_size=500)

# 2. 自动解析并切块
chunks = parser.process_file("samples/test_report.docx")

# 3. 输出结构预览
for chunk in chunks:
    print(chunk["metadata"])  # 例如: {'source': 'test_report.docx', 'type': 'docx'}
    print(chunk["content"])   # 分块的纯文本内容
```

### 步骤四：对接向量检索库（扩展）
解析输出的结果列表，直接支持遍历输入给你的 `HybridRAGEngine` 的 `add_documents` 接口：
```python
engine.add_documents(chunks)
```

## 4. AI 研发踩坑记录与最佳实践 (Pitfalls & Best Practices)

在实际构建基于 LLM 的文档处理器时，我们总结了以下核心避坑指南：

### ⚠️ 经典导包陷阱：PyMuPDF 与 fitz 同名冲突
- **问题症状**：运行 `import fitz` 时，提示 `ModuleNotFoundError: No module named 'frontend'`。
- **根本原因**：在 PyPI 仓库中有一个古老且废弃的包就叫 `fitz`。如果不小心执行了 `pip install fitz`，它会覆盖掉 `pymupdf` 提供的 `fitz` 模块。
- **解决方案**：永远不要安装 `fitz` 包！必须执行 `pip uninstall -y fitz` 清理假包，并严格通过 `pip install pymupdf` 安装。代码里的引用依然是 `import fitz`。

### 💡 表格数据对 LLM 的友好化转换
- **痛点**：PDF 或 Excel 中的表格如果被直接抽成纯文本，会导致行列错位，LLM 无法识别对应关系（产生幻觉）。
- **最佳实践**：我们在 Excel 处理代码中使用了 `df.to_markdown(index=False)`，将结构化数据直接转化为 **Markdown 管道符表格**。主流的大模型（如 DeepSeek, GPT-4, Claude）在预训练时见过海量 Markdown 数据，对 Markdown Table 的空间推理能力极强。

### 🔪 分块 (Chunking) 的进阶优化空间
虽然本项目使用定长字符截断（如 500 字），但到了生产深水区，你可以继续在此架构上升级：
1. **重叠分块 (Overlap Chunking)**：切割时保留 50 个字符的重叠区间（Overlap），防止关键长句被“腰斩”切断在两个 Chunk 之间而丢失上下文。
2. **语义分块 (Semantic Chunking)**：不再按字数无脑切分，而是利用换行符 `\n\n` 或特定标点符号实现按“段落”或“章节”切块，保持语义完整性。
