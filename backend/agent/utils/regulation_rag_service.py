import os
from dotenv import load_dotenv

from pinecone import Pinecone

from ..core.pinecone_client import PineconeClient

load_dotenv()

# Single source of truth for the combined SOC 2 + GDPR control namespace. Shared by both
# the ingestion script (agent/scripts/data_ingestion.py) and retrieval so the index name
# stays in lockstep. Decoupled from the free-text `framework` label, which is now only
# used to build the semantic query string.
REGULATION_NAMESPACE = "SOC2&GDPR"


class RegulationRAGService:
    def __init__(self, index: str, namespace: str = REGULATION_NAMESPACE, pc: Pinecone | None = None):
        self.pc = pc or Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.vector_store = PineconeClient(index_name=index, pc=self.pc)
        self.namespace = namespace

    def query_regulations(
        self,
        query: str,
        namespace: str | None,
        top_k: int = 5,
        rerank_top_k: int = 5,
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
                rerank_top_k=rerank_top_k,
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
                        # `criterion_text` / `testing_approach` are the v3 index field
                        # names; we map them back to the stable internal keys the rest of
                        # the pipeline consumes (requirement / testing_criteria).
                        "requirement": result.fields["criterion_text"],
                        "points_of_focus": result.fields["points_of_focus"],
                        "source_code_relevance": result.fields["source_code_relevance"],
                        "policy_assertion": (result.fields["policy_assertion"] if "policy_assertion" in result.fields else None),
                        "keywords": result.fields["keywords"],
                        "artifact_types": result.fields["artifact_types"],
                        "testing_criteria": result.fields["testing_approach"],
                        "evidence_indicator": result.fields["evidence_indicators"],
                        "source_code_signal": result.fields["source_code_signal"],
                        "severity": result.fields["severity"]
                    }
                )
        return formatted_results
