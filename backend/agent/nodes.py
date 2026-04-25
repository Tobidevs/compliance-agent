import asyncio
import os
from typing import Literal
from langchain_pinecone._utilities import cosine_similarity
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field


from .prompts import POLICY_EXTRACTION_PROMPT, POLICY_VALIDATION_PROMPT
from .state import ComplianceAgentState, PolicyExtractionResults, PolicyValidationResults
from .utils.regulation_rag_service import RegulationRAGService
from .utils.policy_rag_service import PolicyRAGService


regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)

model = init_chat_model(model="anthropic:claude-haiku-4-5")
policy_extraction_model = model.with_structured_output(PolicyExtractionResults)
policy_validation_model = model.with_structured_output(PolicyValidationResults)


# def format_2d_matrix(
#     matrix,
#     row_labels: list[str] | None = None,
#     col_labels: list[str] | None = None,
#     precision: int = 3,
# ) -> str:
#     rows = matrix.tolist() if hasattr(matrix, "tolist") else matrix
#     if not rows:
#         return "(empty matrix)"

#     row_count = len(rows)
#     col_count = len(rows[0]) if rows[0] else 0
#     row_labels = row_labels or [f"R{i + 1}" for i in range(row_count)]
#     col_labels = col_labels or [f"C{i + 1}" for i in range(col_count)]

#     str_rows = [[f"{float(value):.{precision}f}" for value in row] for row in rows]
#     row_label_width = max(len(""), *(len(label) for label in row_labels))
#     col_widths = [
#         max(len(col_labels[i]), *(len(str_rows[r][i]) for r in range(row_count)))
#         for i in range(col_count)
#     ]

#     header = " " * (row_label_width + 2) + " ".join(
#         col_labels[i].rjust(col_widths[i]) for i in range(col_count)
#     )

#     lines = [header]
#     for i, row in enumerate(str_rows):
#         line = (
#             row_labels[i].ljust(row_label_width)
#             + " | "
#             + " ".join(row[j].rjust(col_widths[j]) for j in range(col_count))
#         )
#         lines.append(line)

#     return "\n".join(lines)


# def best_claim_per_requirement(
#     matrix,
#     claims: list[str],
#     requirements: list[str],
# ):
#     rows = matrix.tolist() if hasattr(matrix, "tolist") else matrix
#     if not rows:
#         return []

#     row_count = len(rows)
#     col_count = len(rows[0]) if rows[0] else 0
#     best_pairs = []

#     for col_idx in range(col_count):
#         best_row_idx = max(
#             range(row_count), key=lambda row_idx: float(rows[row_idx][col_idx])
#         )
#         best_score = float(rows[best_row_idx][col_idx])
#         best_pairs.append(
#             {
#                 "requirement_index": col_idx,
#                 "requirement": requirements[col_idx],
#                 "claim_index": best_row_idx,
#                 "claim": claims[best_row_idx],
#                 "score": best_score,
#             }
#         )

#     return best_pairs


# 1st Node: Extract regulations and policies from RAG services based on the input framework and category
async def extraction_node(state: ComplianceAgentState):

    regulation_query = f"Retrieve {state['framework']} control requirements for category {state['category']}. "
    policy_query = (
        f"Retrieve compliance policies relevant to {state['framework']} "
        f"and category {state['category']}."
    )

    regulation_task = asyncio.to_thread(
        regulation_service.query_regulations,
        query=regulation_query,
        top_k=5,
        namespace=state["framework"].lower(),
        category=state["category"],
    )
    policy_task = asyncio.to_thread(
        policy_service.query_policies,
        query=policy_query,
        top_k=5,
    )

    regulation_results, policy_results = await asyncio.gather(
        regulation_task, policy_task
    )
    formatted_regulations = regulation_service.format_regulation_results(
        regulation_results
    )
    formatted_policies = policy_service.format_policy_results(policy_results)

    return {"regulations": formatted_regulations, "policies": formatted_policies}


async def policy_validator_node(state: ComplianceAgentState):

    extracted_policies = policy_extraction_model.invoke(
        [
            HumanMessage(
                content=POLICY_EXTRACTION_PROMPT.format(
                    regulations="\n\n".join(
                        [
                            f"{reg['title']} ({reg['control_id']}): {reg['requirement']}"
                            for reg in state["regulations"]
                        ]
                    ),
                    excerpts="\n\n".join(
                        [
                            f"Policy Excerpt {i+1}: {policy['content']}"
                            for i, policy in enumerate(state["policies"])
                        ]
                    ),
                )
            )
        ]
    )
    
    validation_results = policy_validation_model.invoke(
        [
            HumanMessage(
                content=POLICY_VALIDATION_PROMPT.format(
                    extraction_results=extracted_policies.results
                )
                
            )
        ]
    )
    

    # claims = [f"{result.policy_assertion}" for result in response.results]
    # requirements = [f"{reg['policy_assertion']}" for reg in state["regulations"]]

    # claim_embeddings = [policy_service.openai_client.embed_batch(claims)]
    # requirement_embeddings = [policy_service.openai_client.embed_batch(requirements)]
    # similarity_scores = [
    #     cosine_similarity(claim_emb, req_emb)
    #     for claim_emb in claim_embeddings
    #     for req_emb in requirement_embeddings
    # ]

    # if similarity_scores:
    #     similarity_matrix = similarity_scores[0]
    #     similarity_table = format_2d_matrix(
    #         similarity_matrix,
    #         row_labels=[f"Claim {i + 1}" for i in range(len(claims))],
    #         col_labels=[f"Req {i + 1}" for i in range(len(requirements))],
    #     )
    #     print("Similarity Matrix:\n" + similarity_table)

    #     best_matches = best_claim_per_requirement(
    #         similarity_matrix,
    #         claims=claims,
    #         requirements=requirements,
    #     )
    #     print("\nBest Claim Per Requirement:")
    #     for match in best_matches:
    #         print(
    #             f"Req {match['requirement_index'] + 1} -> "
    #             f"Claim {match['claim_index'] + 1} "
    #             f"(score={match['score']:.3f})"
    #         )
    #         print(f"  Requirement: {match['requirement']}")
    #         print(f"  Claim: {match['claim']}")

    return {"policy_validation_results": validation_results.results}
