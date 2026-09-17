import sys
from unittest.mock import MagicMock

# Monkey-patch langchain_community.chat_models.vertexai 
# 因为某些版本的 ragas 强制导入这个不存在的路径
try:
    import langchain_community.chat_models.vertexai
except ImportError:
    mock_module = MagicMock()
    sys.modules["langchain_community.chat_models.vertexai"] = mock_module
    sys.modules["langchain_community.llms"] = mock_module

import os
import pandas as pd
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. 配置
load_dotenv()

# 设置评估模型 (裁判)
# 注意：裁判模型需要较强的逻辑能力，推荐用 gpt-4o 或 deepseek-v4-pro
eval_llm = ChatOpenAI(model_name="deepseek-chat") 

# 设置嵌入模型 (用于评估内部的相似度计算)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 2. 准备 RepoSense 的检索器
DB_DIR = "projects/repo_sense/chroma_db"
vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

def run_automated_evaluation():
    print("🚀 正在启动自动化 RAGAS 评估...")

    # 3. 定义测试集 (问题 + 标准答案)
    test_data = [
        {
            "question": "RepoSense 项目的 indexer.py 是用来做什么的？",
            "ground_truth": "indexer.py 是代码库索引器，负责扫描核心代码目录中的 .py 和 .md 文件，将其切分为代码片段，并通过嵌入模型存储到 Chroma 向量数据库中。"
        },
        {
            "question": "在这个项目中，如何启动 MCP 服务端？",
            "ground_truth": "在这个项目中，MCP 服务端是通过运行 03-mcp/01_simple_server.py 启动的。它是基于 stdio 协议的。"
        }
    ]

    # 4. 模拟 Agent 运行，收集 Context 和 Answer
    eval_dataset = []
    for item in test_data:
        print(f"正在测试问题: {item['question']}")
        
        # 检索上下文
        docs = retriever.invoke(item['question'])
        contexts = [doc.page_content for doc in docs]
        
        # 生成回答 (模拟 Agent 节点逻辑)
        model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
        context_str = "\n".join(contexts)
        prompt = f"基于以下代码背景回答问题：\n{context_str}\n\n问题：{item['question']}"
        response = model.invoke(prompt)
        
        eval_dataset.append({
            "question": item['question'],
            "contexts": contexts,
            "answer": response.content,
            "ground_truth": item['ground_truth']
        })

    # 5. 转换为 Ragas 要求的 Dataset 格式
    dataset = Dataset.from_list(eval_dataset)

    # 6. 执行评估
    print("\n--- 正在调用裁判模型进行量化打分 (请耐心等待) ---")
    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=eval_llm,
        embeddings=embeddings
    )

    # 7. 展示结果
    df = result.to_pandas()
    print("\n📊 评估结果汇总:")
    # 打印所有可用的列，避免 KeyError
    print(df.head())
    
    print("\n📈 平均分:")
    print(result)

if __name__ == "__main__":
    run_automated_evaluation()
