import time
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

start = time.time()
db = Chroma(persist_directory='./chroma_db', embedding_function=DeterministicFakeEmbedding(size=384))
docs = db.get()
documents = [Document(page_content=txt, metadata=meta) for txt, meta in zip(docs['documents'], docs['metadatas'])]
print(f"Loaded {len(documents)} docs from Chroma in {time.time() - start:.2f}s")

start_bm25 = time.time()
import jieba
def chinese_tokenizer(text):
    return list(jieba.cut(text))
bm25 = BM25Retriever.from_documents(documents, preprocess_func=chinese_tokenizer)
print(f"Built BM25 in {time.time() - start_bm25:.2f}s")
