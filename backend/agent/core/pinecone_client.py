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
        rerank_top_k: int,
        vector: list[float],
        sparse_values: list[float],
        sparse_indices: list[int],
        filter: dict | None = None,
        rank_field: str = "embedding_text",
    ):
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
                "top_n": rerank_top_k,
                # Rank against the same composite text that was embedded at ingestion
                # so dense retrieval and reranking judge controls on the same surface.
                "rank_fields": [rank_field],
            },
        )

        return ranked_results.result.hits

    def fetch_by_filter(
        self,
        namespace: str,
        vector: list[float],
        sparse_values: list[float],
        sparse_indices: list[int],
        filter: dict,
        top_k: int = 50,
    ):
        """
        Exhaustively return every record matching `filter` (e.g. all controls in a
        category), ranked by relevance to the supplied vector but never truncated
        below the match count. Pinecone serverless requires a vector even for a
        metadata-scoped fetch, so we pass one for ordering only — `top_k` is sized
        well above the largest category so no control is silently dropped.
        """
        results = self.index.search(
            namespace=namespace,
            query={
                "top_k": top_k,
                "vector": {
                    "values": vector,
                    "sparse_values": sparse_values,
                    "sparse_indices": sparse_indices,
                },
                "filter": filter,
            },
        )
        return results.result.hits
