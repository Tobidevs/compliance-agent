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


def ingest_compliance_data(file_path: str):
    df = pd.read_csv(file_path)

    dense_embeddings = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[row["criterion_text"] for _, row in df.iterrows()],
        parameters={"input_type": "passage", "truncate": "END"},
    )

    sparse_embeddings = pc.inference.embed(
        model="pinecone-sparse-english-v0",
        inputs=[row["criterion_text"] for _, row in df.iterrows()],
        parameters={"input_type": "passage", "truncate": "END"},
    )

    records = []
    for d, de, se in zip(
        df.to_dict(orient="records"), dense_embeddings, sparse_embeddings
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
                },
            }
        )

    index.upsert(vectors=records, namespace=target_namespace)


csv_path = os.path.join(os.path.dirname(__file__), "SOC2_GDPR_Controls_v3.csv")
ingest_compliance_data(csv_path)
print(
    f"Data ingestion completed successfully in index '{index_name}' namespace '{target_namespace}'."
)
