import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_classic.chains import RetrievalQA
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. 加载环境变量 (获取 OPENAI_API_KEY)
load_dotenv()

def run_basic_rag():
    print("--- 步骤 1: 加载文档 ---")
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "ai_learning_guide.txt")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    print(f"成功加载文档，内容长度: {len(documents[0].page_content)}")

    print("\n--- 步骤 2: 文本切分 (Splitting) ---")
    # 将长文档切分为 200 字符左右的小块，块之间有 50 字符的重叠以保持上下文
    text_splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=50, separator="\n")
    texts = text_splitter.split_documents(documents)
    print(f"文档已切分为 {len(texts)} 个代码块。")

    print("\n--- 步骤 3: 嵌入并存储 (Embedding & Vector Store) ---")
    # 初始化嵌入模型，使用本地 HuggingFace 模型 (避免 DeepSeek API 暂时不支持 Embedding 的问题)
    # 这会下载一个约 100MB 的模型并在本地运行
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    # 使用 Chroma 在内存中创建向量数据库
    vectorstore = Chroma.from_documents(
        documents=texts, 
        embedding=embeddings,
        collection_name="learning_collection"
    )
    print("向量数据库构建完成（已使用本地嵌入模型）。")

    print("\n--- 步骤 4: 问答测试 (QA) ---")
    # 初始化聊天模型 (由于 API Key 已配置，这部分仍使用 DeepSeek)
    llm = ChatOpenAI(model_name="deepseek-v4-flash", temperature=0)

    # 创建检索问答链
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # "stuff" 表示直接把检索到的内容塞进提示词
        retriever=vectorstore.as_retriever()
    )

    # 提问
    query = "什么是 RAG？它的核心组件有哪些？"
    print(f"用户提问: {query}")
    
    response = qa_chain.invoke(query)
    print(f"\n模型回答:\n{response['result']}")

if __name__ == "__main__":
    run_basic_rag()
