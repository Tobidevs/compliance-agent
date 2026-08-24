import json
import os
import re
import tempfile

from contextlib import nullcontext

import braintrust
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from agent.utils.policy_rag_service import PolicyRAGService
from agent.agent import compliance_agent
from .observability import langfuse_enabled, langfuse_trace

router = APIRouter()
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
policy_service = PolicyRAGService(persist_directory=CHROMA_PERSIST_DIRECTORY)

# policy_id keys documents in a shared Chroma collection, so it must be an opaque slug.
POLICY_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
MAX_POLICY_UPLOAD_BYTES = max(
    1024, int(os.getenv("MAX_POLICY_UPLOAD_BYTES", str(20 * 1024 * 1024)))
)
_UPLOAD_CHUNK_BYTES = 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]")


def _format_stream_error(error: Exception) -> str:
    raw_message = " ".join(str(error).split()).strip()
    lowered_message = raw_message.lower()

    if (
        "rate limit" in lowered_message
        or "too many requests" in lowered_message
        or "429" in lowered_message
        or "quota" in lowered_message
    ):
        return (
            "Rate limit reached while running the compliance agent. "
            "Please wait a moment and try again."
        )

    if "not found" in lowered_message and "repo" in lowered_message:
        return (
            "Repository not found or inaccessible. "
            "Please verify the repository owner and name, then try again."
        )

    if "timed out" in lowered_message or "timeout" in lowered_message:
        return (
            "The compliance run timed out before completion. "
            "Please try again in a moment."
        )

    if not raw_message:
        return "The compliance agent failed unexpectedly. Please try again."

    return f"Compliance agent failed: {raw_message}"

class StreamRequest(BaseModel):
    framework: str
    category: str
    source_code_categories: list[str]
    repo_owner: str
    repo_name: str

def _safe_filename(raw: str | None) -> str:
    """Store a display name only; the uploader never influences the path we write to."""
    cleaned = _SAFE_FILENAME_RE.sub("_", (raw or "policy.pdf").strip())
    return cleaned[:128] or "policy.pdf"


@router.post("/upload-policy")
async def upload_policy(
    policy_id: str = Query(..., pattern=POLICY_ID_PATTERN, max_length=64),
    policy_file: UploadFile = File(...),
):
    file_path = None
    try:
        header = await policy_file.read(5)
        await policy_file.seek(0)
        if header != b"%PDF-":
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid PDF file.",
            )

        # Suffix is fixed rather than derived from the uploaded filename, and the body is
        # streamed so an oversized upload is rejected instead of buffered to disk in full.
        with tempfile.NamedTemporaryFile(
            prefix="policy_", suffix=".pdf", delete=False
        ) as temp_file:
            file_path = temp_file.name
            uploaded_bytes = 0
            while chunk := await policy_file.read(_UPLOAD_CHUNK_BYTES):
                uploaded_bytes += len(chunk)
                if uploaded_bytes > MAX_POLICY_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Policy file exceeds the {MAX_POLICY_UPLOAD_BYTES:,}-byte upload limit.",
                    )
                temp_file.write(chunk)

        policy_service.add_policy(
            policy_id=policy_id,
            policy_file=file_path,
            metadata={"filename": _safe_filename(policy_file.filename)},
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload policy: {e}")
    finally:
        await policy_file.close()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    return {"message": "File uploaded successfully."}


@router.post("/stream")
async def stream_results(
    request: StreamRequest
):
    initial_state = {
        "framework": request.framework,
        "category": (
            request.source_code_categories[0]
            if isinstance(request.source_code_categories, list)
            else request.source_code_categories
        ),
        "source_code_categories": request.source_code_categories,
        "repo_owner": request.repo_owner,
        "repo_name": request.repo_name,
    }

    def _json_default(value):
        if isinstance(value, BaseModel):
            return value.model_dump()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _normalize_custom_event(payload):
        if isinstance(payload, dict) and isinstance(payload.get("type"), str):
            return payload

        return {
            "type": "status",
            "data": payload,
        }

    repo = f"{initial_state['repo_owner']}/{initial_state['repo_name']}"
    trace_input = {
        "framework": initial_state["framework"],
        "category": initial_state["category"],
        "repo": repo,
        "source_code_categories": initial_state["source_code_categories"],
    }

    # Pass the Langfuse handler into the graph so every nested LLM call (evidence and
    # validation subagents) is captured automatically; group runs by repo via session_id.
    use_langfuse = langfuse_enabled()
    config = {"callbacks": [CallbackHandler()]} if use_langfuse else None
    langfuse_cm = (
        langfuse_trace(
            name="compliance_run",
            input=trace_input,
            session_id=repo,
            tags=[initial_state["framework"], "compliance-run"],
            metadata={
                "repo": repo,
                "source_code_categories": ", ".join(
                    initial_state["source_code_categories"]
                ),
            },
        )
        if use_langfuse
        else nullcontext()
    )

    async def event_generator():
        with braintrust.start_span(
            name="compliance_run",
            input=trace_input,
        ) as span, langfuse_cm as lf_span:
            try:
                async for mode, data in compliance_agent.astream(
                    initial_state, stream_mode=["custom", "updates"], config=config
                ):
                    if mode == "custom":
                        yield f"data: {json.dumps(_normalize_custom_event(data), default=_json_default)}\n\n"
                    elif mode == "updates":
                        yield f"data: {json.dumps({
                            'type': 'update',
                            'data': data
                        }, default=_json_default)}\n\n"

                span.log(output={"status": "completed"})
                if lf_span is not None:
                    lf_span.update(output={"status": "completed"})
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as error:
                span.log(output={"status": "error", "message": str(error)})
                if lf_span is not None:
                    lf_span.update(
                        output={"status": "error", "message": str(error)}
                    )
                yield f"data: {json.dumps({'type': 'error', 'message': _format_stream_error(error)})}\n\n"
            finally:
                if use_langfuse:
                    get_client().flush()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/health")
async def health_check():
    return {"status": "ok"}
