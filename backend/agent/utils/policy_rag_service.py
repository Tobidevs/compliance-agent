from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader

from ..core.chroma_client import ChromaClient
from ..core.openai_client import OpenAIClient

load_dotenv()


class PolicyRAGService:
    def __init__(self, persist_directory: str | None = None):
        persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR", "./chroma_db"
        )
        self.vector_store = ChromaClient(
            collection_name="compliance-policies",
            persist_directory=persist_directory,
        )
        self.openai_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))

    def add_policy(self, policy_id: str, policy_file: str, metadata: dict):
        loader = PyPDFLoader(policy_file)
        try:
            docs = loader.load()
        except Exception as e:
            raise ValueError(
                "Invalid PDF content. The uploaded file could not be parsed."
            ) from e

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

        try:
            chunks = text_splitter.split_documents(docs)
            chunk_texts = [chunk.page_content for chunk in chunks]
            chunk_ids = [f"{policy_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_metadata.append(
                    {
                        "policy_id": policy_id,
                        "chunk_index": i,
                        **metadata,
                        **(chunk.metadata or {}),
                    }
                )
            embeddings = [
                self.openai_client.get_embedding(text) for text in chunk_texts
            ]

            self.vector_store.upsert(
                documents=chunk_texts,
                ids=chunk_ids,
                embeddings=embeddings,
                metadata=chunk_metadata,
            )
        except Exception as e:
            raise ValueError(
                "Failed to process the PDF content and store it in the vector database."
            ) from e

    def query_policies(self, query: str, top_k: int = 5):
        embedding = self.openai_client.get_embedding(query)
        results = self.vector_store.query(query_embedding=embedding, top_k=top_k)
        return results

    def format_policy_results(self, results):
        if not results:
            return []

        ids = (results.get("ids") or [[]])[0]
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        formatted_results = []
        for i, doc_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            formatted_results.append(
                {
                    "id": doc_id,
                    "policy_id": metadata.get("policy_id"),
                    "filename": metadata.get("filename"),
                    "chunk_index": metadata.get("chunk_index"),
                    "content": documents[i] if i < len(documents) else None,
                    "distance": distances[i] if i < len(distances) else None,
                    "rank": i + 1,
                }
            )

        return formatted_results

    def delete_policy(self, policy_id: str):
        self.vector_store.delete(ids=[policy_id])
