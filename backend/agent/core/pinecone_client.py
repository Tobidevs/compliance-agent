import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()


class PineconeClient:
    def __init__(self, index_name: str, pc: Pinecone | None = None):
        self.pc = pc or Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = index_name
        if not self.pc.has_index(index_name):
            self.pc.create_index(
                name=index_name,
                vector_type="dense",
                dimension=1024,
                metric="dotproduct",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self.index = self.pc.Index(index_name)

    def query(
        self,
        namespace: str,
        query: str,
        top_k: int,
        vector: list[float],
        sparse_values: list[float],
        sparse_indices: list[int],
        filter: dict | None = None,
    ):
        # results = self.index.query(
        #     namespace=namespace,
        #     top_k=top_k,
        #     vector=vector,
        #     sparse_vector=sparse_vector,
        #     include_values=False,
        #     include_metadata=True,
        # )
        # ranked_results = self.pc.inference.rerank(
        #     model="bge-reranker-v2-m3",
        #     query=query,
        #     documents=[doc["metadata"] for doc in results["matches"]],
        # )

        ranked_results = self.index.search(
            namespace=namespace,
            query={
                "top_k": top_k,
                "vector": {"values": vector, "sparse_values": sparse_values, "sparse_indices": sparse_indices},
                "filter": filter
            },
            rerank={
                "model": "bge-reranker-v2-m3",
                "query": query,
                "top_n": top_k,
                "rank_fields": ["requirement"],
            },
        )
        return ranked_results.result.hits # todo Validate Response Structure
