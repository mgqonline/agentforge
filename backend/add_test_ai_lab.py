import sys
sys.path.append('..')
import pickle
from document_processor.doc_parser import DocumentProcessor
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_core.documents import Document

processor = DocumentProcessor(chunk_size=800, chunk_overlap=150)
chunks = processor.process_file('../document_processor/samples/test_ai_lab.txt')

db = Chroma(persist_directory='./chroma_db', embedding_function=DeterministicFakeEmbedding(size=384))
docs = [Document(page_content=chunk['content'], metadata=chunk['metadata']) for chunk in chunks]
db.add_documents(docs)
print(f"Added {len(docs)} documents to Chroma.")
