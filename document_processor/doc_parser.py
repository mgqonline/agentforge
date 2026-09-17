"""
统一文档解析器 (Unified Document Parser)
支持格式: PDF, DOCX, XLSX, TXT, MD, CSV, JSON, PPTX, HTML, XML
功能: 将异构文档转化为标准化的文本结构 (Chunks/Texts)，适用于 LLM / RAG。
"""

import os
import io
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from typing import List, Dict, Any

class DocumentProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """主入口，根据文件扩展名自动路由到对应的解析器"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")
            
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.pdf':
            return self._process_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self._process_word(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self._process_excel(file_path)
        elif ext == '.txt':
            return self._process_txt(file_path)
        elif ext == '.md':
            return self._process_md(file_path)
        elif ext == '.csv':
            return self._process_csv(file_path)
        elif ext == '.json':
            return self._process_json(file_path)
        elif ext == '.pptx':
            return self._process_pptx(file_path)
        elif ext in ['.html', '.htm']:
            return self._process_html(file_path)
        elif ext == '.xml':
            return self._process_xml(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于滑动窗口机制对文本进行切分 (解决断层问题)"""
        chunks = []
        text = text.strip()
        if not text:
            return chunks
            
        # 步长 = 区块大小 - 重叠大小
        step = max(self.chunk_size - self.chunk_overlap, 10) 
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.chunk_size]
            chunks.append({
                "content": chunk_text,
                "metadata": metadata.copy()
            })
        return chunks

    def _process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 PDF 文档"""
        chunks = []
        try:
            doc = fitz.open(file_path)
            # PDF 逐页解析
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                if text:
                    meta = {"source": os.path.basename(file_path), "type": "pdf", "page": page_num + 1}
                    chunks.extend(self._chunk_text(text, meta))
            doc.close()
        except Exception as e:
            print(f"PDF 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_word(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 Word 文档 (基于段落和标题的语义切块优化 Semantic Chunking)"""
        chunks = []
        try:
            doc = Document(file_path)
            
            current_chunk_text = ""
            current_heading = "None"
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                    
                # 识别标题，提取结构化特征作为当前段落的上下文
                if para.style.name.startswith('Heading'):
                    current_heading = text
                    # 标题本身也可以加入到文本中，强化语义
                    text = f"[{current_heading}]\n" 
                else:
                    text = f"{text}\n"

                # 如果加上当前段落会超出设定大小，则先将积累的内容作为一个 Semantic Chunk 刷入列表
                if len(current_chunk_text) + len(text) > self.chunk_size and current_chunk_text:
                    meta = {
                        "source": os.path.basename(file_path), 
                        "type": "docx", 
                        "heading": current_heading
                    }
                    chunks.append({"content": current_chunk_text.strip(), "metadata": meta})
                    current_chunk_text = "" # 重置 buffer
                    
                # 积累到当前 buffer 中
                current_chunk_text += text
                
            # 处理文档末尾残留的最后一个 Chunk
            if current_chunk_text.strip():
                meta = {
                    "source": os.path.basename(file_path), 
                    "type": "docx", 
                    "heading": current_heading
                }
                chunks.append({"content": current_chunk_text.strip(), "metadata": meta})

        except Exception as e:
            print(f"Word 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 Excel 数据表（带表头强制保留的滑动窗口切块优化）"""
        chunks = []
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                # 使用优化的基于行数的切块，而非生硬的字数切块
                chunk_row_size = 15
                
                for i in range(0, len(df), chunk_row_size):
                    # 取出当前 15 行的数据
                    df_chunk = df.iloc[i : i+chunk_row_size]
                    
                    # to_markdown(index=False) 能够保证每次切割都会自带完整的表头
                    markdown_text = df_chunk.to_markdown(index=False)
                    
                    meta = {"source": os.path.basename(file_path), "type": "xlsx", "sheet": sheet_name}
                    # 对于表格，我们不调用 self._chunk_text，而是直接将这完整的 Markdown Table 作为单个区块保存
                    chunks.append({"content": markdown_text, "metadata": meta})
        except Exception as e:
            print(f"Excel 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """处理纯文本文件"""
        chunks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            meta = {"source": os.path.basename(file_path), "type": "txt"}
            chunks.extend(self._chunk_text(text, meta))
        except Exception as e:
            print(f"TXT 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_md(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 Markdown 文件"""
        chunks = []
        try:
            from langchain_text_splitters import MarkdownTextSplitter
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            meta = {"source": os.path.basename(file_path), "type": "md"}
            
            splitter = MarkdownTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
            docs = splitter.create_documents([text])
            for doc in docs:
                chunks.append({
                    "content": doc.page_content,
                    "metadata": meta
                })
        except Exception as e:
            print(f"Markdown 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 CSV 数据表（滑动窗口保留表头优化）"""
        chunks = []
        try:
            df = pd.read_csv(file_path)
            chunk_row_size = 15
            for i in range(0, len(df), chunk_row_size):
                df_chunk = df.iloc[i : i+chunk_row_size]
                markdown_text = df_chunk.to_markdown(index=False)
                meta = {"source": os.path.basename(file_path), "type": "csv"}
                chunks.append({"content": markdown_text, "metadata": meta})
        except Exception as e:
            print(f"CSV 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_json(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 JSON 文件"""
        chunks = []
        try:
            import json
            from langchain_text_splitters import RecursiveJsonSplitter
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = {"source": os.path.basename(file_path), "type": "json"}
            
            splitter = RecursiveJsonSplitter(max_chunk_size=self.chunk_size)
            docs = splitter.create_documents(texts=[data])
            for doc in docs:
                chunks.append({
                    "content": doc.page_content,
                    "metadata": meta
                })
        except Exception as e:
            print(f"JSON 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_pptx(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 PPTX 幻灯片文件 (按页切块)"""
        chunks = []
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            for i, slide in enumerate(prs.slides):
                slide_text = []
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        slide_text.append(shape.text.strip())
                text = "\n".join([t for t in slide_text if t])
                if text:
                    meta = {"source": os.path.basename(file_path), "type": "pptx", "slide": i + 1}
                    chunks.extend(self._chunk_text(text, meta))
        except Exception as e:
            print(f"PPTX 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_html(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 HTML 文件 (提取干净的可见文本)"""
        chunks = []
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
            # 移除所有脚本和样式
            for script_or_style in soup(['script', 'style']):
                script_or_style.decompose()
            text = soup.get_text(separator='\n').strip()
            # 清洗连续空行
            text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
            meta = {"source": os.path.basename(file_path), "type": "html"}
            chunks.extend(self._chunk_text(text, meta))
        except Exception as e:
            print(f"HTML 解析失败 {file_path}: {str(e)}")
        return chunks

    def _process_xml(self, file_path: str) -> List[Dict[str, Any]]:
        """处理 XML 文件 (提取所有节点文本)"""
        chunks = []
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                # 使用 lxml-xml 作为解析器
                soup = BeautifulSoup(f, 'lxml-xml')
            text = soup.get_text(separator='\n').strip()
            text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
            meta = {"source": os.path.basename(file_path), "type": "xml"}
            chunks.extend(self._chunk_text(text, meta))
        except Exception as e:
            print(f"XML 解析失败 {file_path}: {str(e)}")
        return chunks

if __name__ == "__main__":
    # 测试脚本
    processor = DocumentProcessor(chunk_size=500)
    samples_dir = "document_processor/samples"
    
    for filename in os.listdir(samples_dir):
        file_path = os.path.join(samples_dir, filename)
        if os.path.isfile(file_path):
            print(f"\n--- 正在解析: {filename} ---")
            result_chunks = processor.process_file(file_path)
            for i, chunk in enumerate(result_chunks):
                print(f"【区块 {i+1}】 Metadata: {chunk['metadata']}")
                print(f"完整内容:\n{chunk['content']}\n{'-'*40}\n")
