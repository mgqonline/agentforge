import os
import logging
from typing import List, Dict, Any

# 设置日志配置 (生产环境必备，绝不要仅仅用 print)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DocIngestion")

# ==========================================
# 1. 统一的数据承载结构 (Document Node)
# 不管底层是 PDF 还是 Excel，最终输出的格式必须统一
# ==========================================
class DocumentNode:
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        # 生产环境中，metadata 极其重要，用于 RAG 检索时的过滤（如日期、作者、页码）
        self.metadata = metadata or {}
        
    def __repr__(self):
        return f"<DocNode length={len(self.content)} source={self.metadata.get('source', 'unknown')}>"

# ==========================================
# 2. 定义解析器基类与各种子类 (适配器模式)
# ==========================================
class BaseParser:
    def parse(self, file_path: str) -> List[DocumentNode]:
        raise NotImplementedError

class PDFParser(BaseParser):
    def parse(self, file_path: str) -> List[DocumentNode]:
        logger.info(f"调用 PDF 解析引擎处理: {file_path}")
        # 在真实生产中：pip install pypdf
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return [DocumentNode(d.page_content, d.metadata) for d in docs]
        except ImportError:
            logger.warning("未检测到 pypdf，启动模拟解析器...")
            return [DocumentNode("这里是 PDF 的第一页提取内容。", {"source": file_path, "page": 1})]

class WordParser(BaseParser):
    def parse(self, file_path: str) -> List[DocumentNode]:
        logger.info(f"调用 Word 解析引擎处理: {file_path}")
        # 在真实生产中：pip install docx2txt
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            return [DocumentNode(d.page_content, d.metadata) for d in docs]
        except ImportError:
            logger.warning("未检测到 docx2txt，启动模拟解析器...")
            return [DocumentNode("这里是 Word 合同的正文提取内容。", {"source": file_path, "author": "Legal Dept"})]

class ExcelParser(BaseParser):
    def parse(self, file_path: str) -> List[DocumentNode]:
        logger.info(f"调用 Excel 解析引擎处理: {file_path}")
        # 在真实生产中：pip install pandas openpyxl
        try:
            import pandas as pd
            # 使用 sheet_name=None 强制读取所有 Sheet
            sheet_dict = pd.read_excel(file_path, sheet_name=None)
            nodes = []
            for sheet_name, df in sheet_dict.items():
                # 填充 NaN 空值，防止大模型幻觉
                df = df.fillna("")
                text_content = f"### Sheet: {sheet_name}\n" + df.to_markdown()
                nodes.append(DocumentNode(text_content, {"source": file_path, "type": "spreadsheet", "sheet": sheet_name}))
            return nodes
        except ImportError:
            logger.warning("未检测到 pandas，启动模拟解析器...")
            return [DocumentNode("| 员工姓名 | 绩效得分 |\n| --- | --- |\n| 张三 | 95 |", {"source": file_path})]

# ==========================================
# 3. 解析工厂 (Factory Pattern)
# 根据后缀名自动路由到对应的解析策略
# ==========================================
class ParserFactory:
    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.pdf':
            return PDFParser()
        elif ext in ['.doc', '.docx']:
            return WordParser()
        elif ext in ['.xls', '.xlsx']:
            return ExcelParser()
        else:
            raise ValueError(f"不支持的文档格式: {ext}")

# ==========================================
# 4. 生产级流水线 (Pipeline)
# 集成 路由 -> 提取 -> 清洗 全生命周期
# ==========================================
class DocumentIngestionPipeline:
    def process_file(self, file_path: str) -> List[DocumentNode]:
        try:
            # 步骤 1: 工厂路由
            parser = ParserFactory.get_parser(file_path)
            
            # 步骤 2: 物理提取
            nodes = parser.parse(file_path)
            
            # 步骤 3: 数据清洗 (Data Cleaning) 生产级不可或缺的一步
            nodes = self._clean_data(nodes)
            
            return nodes
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生严重错误: {e}")
            return []
            
    def _clean_data(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
        logger.info("执行文本脏数据清洗...")
        for node in nodes:
            # 去除连续的多个空行，这会大量浪费大模型的 Token 并干扰注意力机制
            lines = node.content.split('\n')
            node.content = '\n'.join([line for line in lines if line.strip() != ''])
        return nodes

# 测试运行
if __name__ == "__main__":
    print("=== 企业级多格式文档解析流水线测试 ===\n")
    
    pipeline = DocumentIngestionPipeline()
    
    # 模拟用户上传的一批混合文档
    test_files = ["Complex_Annual_Report.pdf", "Complex_Labor_Contract.docx", "Complex_Sales_Database.xlsx"]
    
    for f in test_files:
        print(f"\n📥 正在灌入文档: {f}")
        results = pipeline.process_file(f)
        for r in results:
            print(f"✅ 提取结果: {r} -> 预览: '{r.content[:20]}...'")
