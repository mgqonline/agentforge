import os
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

# 配置索引参数
DB_DIR = "projects/repo_sense/chroma_db"
# 只扫描核心代码目录和根目录下的 md
INCLUDE_DIRS = ["01-prompt-engineering", "02-function-calling", "03-mcp", "04-rag", "05-embedding", "06-agent-basics"]
ROOT_FILES = ["README.md", "GEMINI.md"]

def build_index():
    print(f"🚀 开始构建项目索引...")
    
    docs = []
    
    # 1. 扫描根目录特定文件
    for f in ROOT_FILES:
        if os.path.exists(f):
            try:
                loader = TextLoader(f, encoding="utf-8")
                docs.extend(loader.load())
            except Exception as e:
                print(f"⚠️ 无法加载文件 {f}: {e}")

    # 2. 递归扫描核心目录
    for directory in INCLUDE_DIRS:
        if not os.path.exists(directory):
            continue
            
        print(f"  正在扫描目录: {directory}")
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith((".py", ".md")):
                    file_path = os.path.join(root, file)
                    try:
                        loader = TextLoader(file_path, encoding="utf-8")
                        docs.extend(loader.load())
                    except Exception as e:
                        print(f"⚠️ 无法加载文件 {file_path}: {e}")
    
    print(f"✅ 已成功加载 {len(docs)} 个核心文件。")

    if not docs:
        print("❌ 未找到任何可索引的文件！")
        return

    # 3. 切分代码
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    print(f"✂️ 已切分为 {len(splits)} 个代码片段。")

    # 4. 创建向量库
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    vectorstore = Chroma.from_documents(
        documents=splits, 
        embedding=embeddings, 
        persist_directory=DB_DIR
    )
    print(f"💾 索引已完成并持久化至: {DB_DIR}")

if __name__ == "__main__":
    build_index()
