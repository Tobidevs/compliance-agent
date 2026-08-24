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

    def _embed_query(self, query: str):
        """Embed a query string for hybrid (dense + sparse) search."""
        dense = self.pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=query,
            parameters={"input_type": "query", "truncate": "END"},
        )
        sparse = self.pc.inference.embed(
            model="pinecone-sparse-english-v0",
            inputs=query,
            parameters={"input_type": "query", "truncate": "END"},
        )
        return dense[0], sparse[0]

    def get_controls_for_categories(
        self,
        categories: list[str] | str,
        namespace: str | None = None,
    ):
        """
        Return *every* control belonging to the given category/categories.

        This is the primary path used by the pipeline: the caller already knows
        which categories it wants, so selection is a metadata filter.
        """
        if isinstance(categories, str):
            categories = [categories]

        ns = namespace or self.namespace
        results = []
        for category in categories:
            dense, sparse = self._embed_query(category)
            hits = self.vector_store.fetch_by_filter(
                namespace=ns,
                vector=dense["values"],
                sparse_values=sparse["sparse_values"],
                sparse_indices=sparse["sparse_indices"],
                filter={"category": {"$eq": category}},
            )
            results.extend(hits)
        return results

    def query_regulations(
        self,
        query: str,
        namespace: str | None,
        top_k: int = 5,
        rerank_top_k: int = 5,
        category: str | None = None,
    ):
        """
        Free-text semantic search over controls. Use this when the selection is
        driven by content (a concept, a repo description) rather than a known
        category — for category-scoped retrieval prefer
        `get_controls_for_categories`, which is exhaustive.
        """
        dense, sparse = self._embed_query(query)

        return self.vector_store.query(
            namespace=namespace or self.namespace,
            query=query,
            top_k=top_k,
            rerank_top_k=rerank_top_k,
            vector=dense["values"],
            sparse_values=sparse["sparse_values"],
            sparse_indices=sparse["sparse_indices"],
            filter={"category": {"$eq": category}} if category else None,
        )

    def format_regulation_results(self, results):
        formatted_results = []
        for result in results:
            # Metadata drift in the index must degrade a field, not kill the run.
            fields = getattr(result, "fields", None) or {}
            formatted_results.append(
                    {
                        "framework": fields.get("framework", ""),
                        "control_family": fields.get("control_family", ""),
                        "control_id": fields.get("control_id", ""),
                        "category": fields.get("category", ""),
                        "title": fields.get("title", ""),
                        # `criterion_text` / `testing_approach` are the v3 index field
                        # names; we map them back to the stable internal keys the rest of
                        # the pipeline consumes (requirement / testing_criteria).
                        "requirement": fields.get("criterion_text", ""),
                        "points_of_focus": fields.get("points_of_focus", ""),
                        "source_code_relevance": fields.get("source_code_relevance", ""),
                        "policy_assertion": fields.get("policy_assertion"),
                        "keywords": fields.get("keywords", ""),
                        "artifact_types": fields.get("artifact_types", ""),
                        "testing_criteria": fields.get("testing_approach", ""),
                        "evidence_indicator": fields.get("evidence_indicators", ""),
                        "source_code_signal": fields.get("source_code_signal", ""),
                        "severity": fields.get("severity", ""),
                    }
                )
        return formatted_results
