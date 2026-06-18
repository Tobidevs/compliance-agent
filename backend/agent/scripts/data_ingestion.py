import os
import sys

import pandas as pd
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Allow this script to be run directly (`python agent/scripts/data_ingestion.py`) as well
# as via `-m`, by putting the backend package root on the path before importing from it.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agent.utils.regulation_rag_service import REGULATION_NAMESPACE

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "compliance-frameworks"
target_namespace = REGULATION_NAMESPACE

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        vector_type="dense",
        dimension=1024,
        metric="dotproduct",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
index = pc.Index(index_name)


def _humanize(value) -> str:
    """Turn a pipe-delimited CSV cell into readable prose for embedding."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return ", ".join(part.strip() for part in str(value).split("|") if part.strip())


def build_embedding_text(row: dict) -> str:
    """
    Compose the natural-language "control document" that actually gets embedded.
    """
    parts = [
        f"Category: {row['category']}.",
        f"Control: {row['title']} ({row['control_id']}, {row['framework']}).",
        f"Requirement: {row['criterion_text']}",
    ]
    pof = _humanize(row.get("points_of_focus"))
    if pof:
        parts.append(f"Points of focus: {pof}.")
    keywords = _humanize(row.get("keywords"))
    if keywords:
        parts.append(f"Keywords: {keywords}.")
    scr = str(row.get("source_code_relevance") or "").strip()
    if scr:
        parts.append(f"Implementation signals: {scr}")
    return " ".join(parts)


def ingest_compliance_data(file_path: str):
    df = pd.read_csv(file_path)

    rows = df.to_dict(orient="records")
    embedding_texts = [build_embedding_text(row) for row in rows]

    dense_embeddings = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=embedding_texts,
        parameters={"input_type": "passage", "truncate": "END"},
    )

    sparse_embeddings = pc.inference.embed(
        model="pinecone-sparse-english-v0",
        inputs=embedding_texts,
        parameters={"input_type": "passage", "truncate": "END"},
    )

    records = []
    for d, embedding_text, de, se in zip(
        rows, embedding_texts, dense_embeddings, sparse_embeddings
    ):
        records.append(
            {
                "id": "record_" + str(d["control_id"]),
                "values": de["values"],
                "sparse_values": {
                    "indices": se["sparse_indices"],
                    "values": se["sparse_values"],
                },
                "metadata": {
                    "framework": d["framework"],
                    "control_family": d["control_family"],
                    "control_id": d["control_id"],
                    "category": d["category"],
                    "title": d["title"],
                    "criterion_text": d["criterion_text"],
                    "points_of_focus": d["points_of_focus"],
                    "source_code_relevance": d["source_code_relevance"],
                    "keywords": d["keywords"],
                    "artifact_types": d["artifact_types"],
                    "evidence_indicators": d["evidence_indicators"],
                    "testing_approach": d["testing_approach"],
                    "source_code_signal": d["source_code_signal"],
                    "severity": d["severity"],
                    "embedding_text": embedding_text,
                },
            }
        )

    index.upsert(vectors=records, namespace=target_namespace)


csv_path = os.path.join(os.path.dirname(__file__), "SOC2_GDPR_Controls_v3.csv")
ingest_compliance_data(csv_path)
print(
    f"Data ingestion completed successfully in index '{index_name}' namespace '{target_namespace}'."
)
