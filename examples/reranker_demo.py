import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_community.vectorstores import Chroma

# 引入 LangChain 的上下文压缩与重排模块
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_openai import ChatOpenAI

# 设置环境变量（读取根目录的 .env 文件）
from dotenv import load_dotenv
# 向上跳一级找到根目录的 .env（脚本在 examples 下，根目录是上一级）
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# 如果你没有 .env 文件，也可以在此处解开注释写死：
# os.environ["OPENAI_API_KEY"] = "your_openai_key"

def build_reranker_pipeline():
    print("1. 正在初始化基础检索库...")
    
    # 构建一些干扰项文档，用来展示 Reranker 的强大威力
    sample_text = """
    【文档1】公司食堂的苹果很好吃，每天限量供应 100 个。
    【文档2】关于重排器 (Reranker) 的使用规定：当召回文档超过 10 篇时，必须使用 BGE 或 Cohere API 进行重排，仅取 Top-3。
    【文档3】苹果公司今天发布了最新款的 iPhone 和 Mac 电脑。
    【文档4】生产环境的数据库推荐使用 Pinecone，因为它支持海量并发。
    【文档5】如果你想吃水果，推荐去买一点香蕉和苹果。
    """
    
    with open("temp_rerank_docs.txt", "w", encoding="utf-8") as f:
        f.write(sample_text)
        
    loader = TextLoader("temp_rerank_docs.txt", encoding="utf-8")
    docs = loader.load()
    
    # 切片
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=0)
    splits = text_splitter.split_documents(docs)

    # 由于你使用了 DeepSeek 作为 OpenAI 的平替，而它目前不支持 Embeddings 向量接口，
    # 我们这里使用 LangChain 自带的 DeterministicFakeEmbedding（假嵌入）来模拟基础检索。
    # 这正好完美契合我们的实验：基础检索出来的结果是随机垃圾，然后让 LLM 重排器大浪淘沙！
    fake_embeddings = DeterministicFakeEmbedding(size=1536)
    vectorstore = Chroma.from_documents(documents=splits, embedding=fake_embeddings)
    
    # 基础检索器：一次性捞出所有（比如捞出 K=5 篇）
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    print("2. 正在组装基于 LLM 的文档压缩重排器...")
    # 既然没有 Cohere，我们可以利用 OpenAI 的 LLM 自身来做上下文压缩和重排
    # 由于你的环境变量是 DeepSeek，我们需要显式指定模型名为 deepseek-chat
    llm = ChatOpenAI(temperature=0, model="deepseek-chat", base_url="https://api.deepseek.com/v1")
    compressor = LLMChainExtractor.from_llm(llm)
    
    # 使用 ContextualCompressionRetriever 将【重排器】和【基础检索器】串联
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, 
        base_retriever=base_retriever
    )
    
    return base_retriever, compression_retriever

if __name__ == "__main__":
    # 运行依赖: pip install langchain-cohere
    try:
        base_retriever, compression_retriever = build_reranker_pipeline()
        
        question = "我应该使用什么重排器？"
        print(f"\n用户提问: {question}\n")
        
        # ------------------------------------------------------------------
        # 对比实验 A：没有重排器的基础向量检索
        # ------------------------------------------------------------------
        print("=== ❌ 实验 A：仅使用基础检索 (余弦相似度) ===")
        # 余弦相似度往往只看字面，由于文档太短或干扰多，可能会召回很多不相干的内容
        base_docs = base_retriever.invoke(question)
        for i, doc in enumerate(base_docs):
            print(f"召回结果 {i+1}: {doc.page_content.strip()}")
            
        print("\n" + "="*50 + "\n")
        
        # ------------------------------------------------------------------
        # 对比实验 B：加入了 Cohere Reranker 的高级检索
        # ------------------------------------------------------------------
        print("=== ✅ 实验 B：加上 LLM 文档压缩重排器 ===")
        # 重排器会精准判断，剔除无关干扰，提取关键信息
        reranked_docs = compression_retriever.invoke(question)
        for i, doc in enumerate(reranked_docs):
            print(f"【最终留下 Top-{i+1}】: {doc.page_content.strip()}")
            
    except Exception as e:
        print("\n[提示] 运行失败。需要设置 OPENAI_API_KEY 才能真实运行。详细报错：", e)
    finally:
        if os.path.exists("temp_rerank_docs.txt"):
            os.remove("temp_rerank_docs.txt")
