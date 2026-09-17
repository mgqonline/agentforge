import sys
import os
import pickle
from rag_engine import RAGEngine
from document_processor.doc_parser import DocumentProcessor
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_core.documents import Document

processor = DocumentProcessor(chunk_size=800, chunk_overlap=150)
chunks = processor.process_file('../document_processor/samples/test.csv')

db = Chroma(persist_directory='./chroma_db', embedding_function=DeterministicFakeEmbedding(size=384))
docs = [Document(page_content=chunk['content'], metadata=chunk['metadata']) for chunk in chunks]
db.add_documents(docs)
print(f"Added {len(docs)} documents to Chroma.")

# Update the pickled BM25 index as well
bm25_path = './chroma_db/bm25.pickle'
with open(bm25_path, 'rb') as f:
    bm25 = pickle.load(f)
bm25.add_documents(docs)
with open(bm25_path, 'wb') as f:
    pickle.dump(bm25, f)
print("Updated BM25 index.")
