import os
from dotenv import load_dotenv

from pinecone import Pinecone

from ..core.pinecone_client import PineconeClient

load_dotenv()


class RegulationRAGService:
    def __init__(self, index: str, namespace: str = "soc2", pc: Pinecone | None = None):
        self.pc = pc or Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.vector_store = PineconeClient(index_name=index, pc=self.pc)
        self.namespace = namespace

    def query_regulations(
        self,
        query: str,
        namespace: str | None,
        top_k: int = 5,
        category: str | None = None,
    ):
        dense_query_embedding = self.pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=query,
            parameters={"input_type": "query", "truncate": "END"},
        )

        sparse_query_embedding = self.pc.inference.embed(
            model="pinecone-sparse-english-v0",
            inputs=query,
            parameters={"input_type": "query", "truncate": "END"},
        )

        results = []
        for d, s in zip(dense_query_embedding, sparse_query_embedding):
            query_response = self.vector_store.query(
                namespace=namespace or self.namespace,
                query=query,
                top_k=top_k,
                vector=d["values"],
                sparse_values=s["sparse_values"],
                sparse_indices=s["sparse_indices"],
                filter={"category": {"$eq": category}} if category else None,
            )
            results.extend(query_response)

        return results

    def format_regulation_results(self, results):
        formatted_results = []
        for result in results:
            formatted_results.append(
                    {
                        "framework": result.fields["framework"],
                        "control_family": result.fields["control_family"],
                        "control_id": result.fields["control_id"],
                        "category": result.fields["category"],
                        "title": result.fields["title"],
                        "requirement": result.fields["requirement"],
                        "keywords": result.fields["keywords"],
                        "artifact_types": result.fields["artifact_types"],
                        "testing_criteria": result.fields["testing_criteria"],
                        "evidence_indicator": result.fields["evidence_indicator"],
                        "severity": result.fields["severity"]
                    }
                )
        return formatted_results
