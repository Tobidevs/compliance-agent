import pandas as pd
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "compliance-frameworks"

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
        inputs=[row["requirement"] for _, row in df.iterrows()],
        parameters={"input_type": "passage", "truncate": "END"},
    )

    sparse_embeddings = pc.inference.embed(
        model="pinecone-sparse-english-v0",
        inputs=[row["requirement"] for _, row in df.iterrows()],
        parameters={"input_type": "passage", "truncate": "END"},
    )

    records = []
    for d, de, se in zip(df.to_dict(orient="records"), dense_embeddings, sparse_embeddings):
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
                    "requirement": d["requirement"],
                    "keywords": d["keywords"],
                    "artifact_types": d["artifact_types"],
                    "testing_criteria": d["testing_criteria"],
                    "evidence_indicator": d["evidence_indicators"],
                    "severity": d["severity"]
                },
            }
        )

    index.upsert(vectors=records, namespace="soc2")

csv_path = os.path.join(os.path.dirname(__file__), "SOC2 Controls Refactored.csv")
ingest_compliance_data(csv_path)
print("Data ingestion completed successfully.")
