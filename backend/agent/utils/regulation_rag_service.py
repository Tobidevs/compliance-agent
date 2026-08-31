import os
import threading
import time
from dotenv import load_dotenv

from pinecone import Pinecone

from ..core.pinecone_client import PineconeClient

load_dotenv()

# Single source of truth for the combined SOC 2 + GDPR control namespace. Shared by both
# the ingestion script (agent/scripts/data_ingestion.py) and retrieval so the index name
# stays in lockstep. Decoupled from the free-text `framework` label, which is now only
# used to build the semantic query string.
REGULATION_NAMESPACE = "SOC2&GDPR"

# The control corpus is a static 37-row CSV, but every run re-embedded and re-fetched all
# 12 categories. A TTL keeps it refreshable after a re-ingestion without paying per run.
CONTROL_CACHE_TTL_SECONDS = float(os.getenv("CONTROL_CACHE_TTL_SECONDS", "900"))

# Keyed by (index, namespace, category); read from asyncio worker threads, hence the lock.
_control_cache: dict[tuple, tuple[float, list]] = {}
_control_cache_lock = threading.Lock()


def clear_control_cache() -> None:
    """Drop the cached corpus, e.g. straight after re-running data ingestion."""
    with _control_cache_lock:
        _control_cache.clear()


class RegulationRAGService:
    def __init__(self, index: str, namespace: str = REGULATION_NAMESPACE, pc: Pinecone | None = None):
        self.pc = pc or Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.vector_store = PineconeClient(index_name=index, pc=self.pc)
        self.namespace = namespace
        self.index_name = index

    def _embed_queries(self, queries: list[str]):
        """Embed many query strings in one dense + one sparse round-trip, not two per query."""
        dense = self.pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=queries,
            parameters={"input_type": "query", "truncate": "END"},
        )
        sparse = self.pc.inference.embed(
            model="pinecone-sparse-english-v0",
            inputs=queries,
            parameters={"input_type": "query", "truncate": "END"},
        )
        return [(dense[i], sparse[i]) for i in range(len(queries))]

    def _embed_query(self, query: str):
        """Embed a query string for hybrid (dense + sparse) search."""
        return self._embed_queries([query])[0]

    def _cache_key(self, namespace: str, category: str) -> tuple:
        return (self.index_name, namespace, category)

    def _cached_controls(self, namespace: str, category: str):
        """Cached hits for one category, or None on a miss. An empty category caches as []."""
        key = self._cache_key(namespace, category)
        with _control_cache_lock:
            entry = _control_cache.get(key)
            if entry is None:
                return None
            expires_at, hits = entry
            if expires_at <= time.monotonic():
                _control_cache.pop(key, None)
                return None
            return hits

    def _cache_controls(self, namespace: str, category: str, hits) -> None:
        with _control_cache_lock:
            _control_cache[self._cache_key(namespace, category)] = (
                time.monotonic() + CONTROL_CACHE_TTL_SECONDS,
                hits,
            )

    def get_controls_for_categories(
        self,
        categories: list[str] | str,
        namespace: str | None = None,
    ):
        """
        Return *every* control belonging to the given category/categories.

        This is the primary path used by the pipeline: the caller already knows
        which categories it wants, so selection is a metadata filter. The vector only
        orders results inside that exhaustive filter, so the embeddings for all uncached
        categories are batched into a single pair of calls rather than two per category.
        """
        if isinstance(categories, str):
            categories = [categories]

        ns = namespace or self.namespace
        pending = list(
            dict.fromkeys(
                category
                for category in categories
                if self._cached_controls(ns, category) is None
            )
        )

        fetched: dict[str, list] = {}
        if pending:
            for category, (dense, sparse) in zip(pending, self._embed_queries(pending)):
                hits = self.vector_store.fetch_by_filter(
                    namespace=ns,
                    vector=dense["values"],
                    sparse_values=sparse["sparse_values"],
                    sparse_indices=sparse["sparse_indices"],
                    filter={"category": {"$eq": category}},
                )
                fetched[category] = hits
                self._cache_controls(ns, category, hits)

        results = []
        for category in categories:
            # Prefer what we just fetched: a zero/short TTL must disable caching, never
            # silently drop controls out of the returned roster.
            hits = fetched.get(category)
            if hits is None:
                hits = self._cached_controls(ns, category) or []
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
