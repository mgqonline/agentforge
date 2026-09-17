# 生产级文档处理解析实践 (Document Ingestion)

在构建企业级 RAG（检索增强生成）系统或文档分析智能体时，往往有 **80% 的精力消耗在非结构化文档的数据清洗与解析上**。大模型再聪明，喂进去乱码或者没有逻辑的换行，也是无米之炊。

## 一、 为什么不能简单地写一个脚本凑合？

在学习阶段，你可能直接用一段 `pdfplumber.open(file)` 就完事了，但在生产环境中会遇到三大坑：
1.  **文件格式杂乱**：用户打包上传一个 ZIP，里面有 PDF、Word、Excel，硬编码会直接崩溃。
2.  **元数据 (Metadata) 丢失**：如果提取了 10 万字，但没有记录“页码”和“来源文件名”，大模型总结后根本无法给出溯源引用（Citation）。
3.  **Token 浪费**：Word 里可能存在大量的空行、特殊换行符；Excel 直接拼成一行大长句会让模型完全丧失对行列关系的理解。

## 二、 生产级框架架构解析

参考代码 [document_parsing_pipeline.py](file:///Users/mac/Documents/project/ailearning/04-rag/document_parsing_pipeline.py)，我们将解析过程进行了标准的软件工程化解耦：

### 1. 统一的数据承载契约 (`DocumentNode`)
所有不同的底层解析包（PyPDF、python-docx、pandas），在吐出数据后，必须被强制塞进统一的 `DocumentNode` 类中。
这个类不仅包含 `content`（文本），还必须包含 `metadata`（字典类型）。在后面的向量数据库存入阶段，这极其重要。

### 2. 工厂路由模式 (`ParserFactory`)
业务代码不应该关心“怎样解析 PDF”。业务代码只管把文件路径丢给 `ParserFactory`，工厂通过文件后缀名匹配，实例化对应的解析器（Adapter）。

### 3. 三大金刚底层包的选型与避坑
*   **PDF (`pypdf` 或 `PyMuPDF/fitz`)**：最推荐 `PyMuPDF`，速度快，对于包含水印、双栏排版的 PDF 处理较好。
*   **Word (`python-docx` / `docx2txt`)**：常规包。注意它们很难完美提取 Word 内部嵌套的图片。
*   **Excel (`pandas`)**：**绝杀技巧**：绝对不要用 `json` 或逗号分隔符喂给大模型。因为大模型是在 Github 极其庞大的 Markdown 数据集上训练的，它对 **Markdown Table** 的理解力最强。所以读入 DataFrame 后，务必使用 `df.to_markdown()` 转换成 Markdown 字符串！

### 4. 必备的数据清洗阀门 (`Data Cleaning`)
解析完成后，流向大模型之前，通过 `_clean_data()` 抹平连续的空白行、去除乱码字符、甚至把超长的文本进行初级切块（Chunking），这是提升生成质量的最后一道防线。
