import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 模拟环境设置（实际运行需要配置真实的 API_KEY）
# os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"

def build_advanced_rag_pipeline():
    print("1. 正在初始化数据和向量库 (Chroma)...")
    
    # ---------------------------------------------------------
    # 步骤 1：准备数据与智能分块 (Chunking)
    # ---------------------------------------------------------
    # 模拟一份企业知识文档的内容
    sample_text = """
    【AI 工程规范 V2.0】
    关于重排器 (Reranker) 的使用规定：
    当召回文档数量超过 10 篇时，必须使用 BGE-Reranker-Large 或者 Cohere Rerank API 进行重排，
    仅取 Top-3 传入大模型的上下文中。这能有效降低幻觉并节省 Token 成本。
    
    关于向量数据库的选型：
    项目组目前推荐本地和测试环境使用 Chroma，生产环境海量并发推荐使用 Pinecone。
    """
    
    # 写入临时文件供加载
    with open("temp_knowledge.txt", "w", encoding="utf-8") as f:
        f.write(sample_text)
        
    loader = TextLoader("temp_knowledge.txt", encoding="utf-8")
    docs = loader.load()
    
    # 使用递归字符分割器，保留语义完整性
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
    splits = text_splitter.split_documents(docs)

    # ---------------------------------------------------------
    # 步骤 2：向量化 (Embedding) 与入库 (Chroma)
    # ---------------------------------------------------------
    # 使用 OpenAI 的 Embedding 模型（你也可以换成开源的 BGE 等）
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
    
    # ---------------------------------------------------------
    # 步骤 3：高阶检索策略 —— 多查询检索 (Multi-Query Retrieval)
    # ---------------------------------------------------------
    # 为什么这是达到 95% 准确率的关键？用户的问题往往表述不清。
    # MultiQueryRetriever 会利用 LLM 把用户的问题重写成多个不同视角的查询，分别检索后再取并集。
    llm = ChatOpenAI(temperature=0)
    retriever = MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(search_kwargs={"k": 2}), 
        llm=llm
    )

    # ---------------------------------------------------------
    # 步骤 4：严格锚定事实的生成 (Generation)
    # ---------------------------------------------------------
    # 精心设计的 Prompt 也是高准确率的保障，必须明确“不知道就别编”
    template = """
    你是一个专业、严谨的问答助手。请严格遵守以下规则：
    1. 你只能基于下面提供的 <context> 上下文信息来回答用户的问题。
    2. 如果在上下文中找不到答案，请直接回答 "根据提供的知识库，我无法回答该问题"，绝对禁止根据你的内部知识进行编造。
    3. 回答要言简意赅，并引用上下文中的关键信息。

    <context>
    {context}
    </context>

    用户问题: {question}
    你的回答:
    """
    custom_rag_prompt = PromptTemplate.from_template(template)

    # 组装 LCEL (LangChain Expression Language) 管道
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

if __name__ == "__main__":
    # 注意：运行此代码需要安装依赖包: pip install langchain langchain-openai langchain-community chromadb
    try:
        rag_chain = build_advanced_rag_pipeline()
        
        print("\n2. 管道构建完成，开始测试查询...")
        question = "生产环境应该用什么向量数据库？重排器要怎么用？"
        print(f"\n用户提问: {question}")
        
        # 执行 RAG 推理
        result = rag_chain.invoke(question)
        
        print("\n=== RAG 最终回答 ===")
        print(result)
        
    except Exception as e:
        print("\n[提示] 运行失败。如果你还没有配置 OPENAI_API_KEY，请在环境中设置后重试。详细报错：", e)
    finally:
        # 清理临时文件
        if os.path.exists("temp_knowledge.txt"):
            os.remove("temp_knowledge.txt")
