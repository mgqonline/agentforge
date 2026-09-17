import os
import pickle
import time
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
import jieba

def chinese_tokenizer(text):
    return list(jieba.cut(text))

print("Loading documents from Chroma...")
db = Chroma(persist_directory='./chroma_db', embedding_function=DeterministicFakeEmbedding(size=384))
docs = db.get()
documents = [Document(page_content=txt, metadata=meta) for txt, meta in zip(docs['documents'], docs['metadatas'])]
print(f"Loaded {len(documents)} docs.")

print("Building BM25 index...")
bm25 = BM25Retriever.from_documents(documents, preprocess_func=chinese_tokenizer)
bm25.k = 2

print("Saving BM25 index to bm25.pickle...")
with open('./chroma_db/bm25.pickle', 'wb') as f:
    pickle.dump(bm25, f)
print("Done!")
