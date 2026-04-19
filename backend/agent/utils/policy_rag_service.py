from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader

from ..core.chroma_client import ChromaClient
from ..core.openai_client import OpenAIClient

class PolicyRAGService:
    def __init__(self):
        self.vector_store = ChromaClient(collection_name="compliance-policies")
        self.openai_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
    
    def add_policy(self, policy_id: str, policy_file: str, metadata: dict):
        loader = PyPDFLoader(policy_file)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        
        chunks = text_splitter.split_documents(docs)
        embeddings = [self.openai_client.get_embedding(chunk.page_content) for chunk in chunks]
        
        self.vector_store.upsert(documents=chunks, embeddings=embeddings)
        
    def query_policies(self, query: str, top_k: int = 5):
        embedding = self.openai_client.get_embedding(query)
        results = self.vector_store.query(
            query_embedding=embedding,
            top_k=top_k
        )
        return results
        
    def delete_policy(self, policy_id: str):
        self.vector_store.delete(ids=[policy_id])
        