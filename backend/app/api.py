import json
import shutil
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.utils.policy_rag_service import PolicyRAGService
from agent.agent import compliance_agent

router = APIRouter()
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
policy_service = PolicyRAGService(persist_directory=CHROMA_PERSIST_DIRECTORY)

class StreamRequest(BaseModel):
    framework: str
    category: str
    source_code_categories: list[str]
    repo_owner: str
    repo_name: str

@router.post("/upload-policy")
async def upload_policy(policy_id: str, policy_file: UploadFile = File(...)):
    filename = policy_file.filename or "policy.pdf"
    suffix = Path(filename).suffix or ".pdf"
    file_path = None
    try:
        header = await policy_file.read(5)
        await policy_file.seek(0)
        if header != b"%PDF-":
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Please upload a valid PDF file.",
            )

        with tempfile.NamedTemporaryFile(
            prefix="policy_", suffix=suffix, delete=False
        ) as temp_file:
            file_path = temp_file.name
            shutil.copyfileobj(policy_file.file, temp_file)

        policy_service.add_policy(
            policy_id=policy_id,
            policy_file=file_path,
            metadata={"filename": policy_file.filename},
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

    async def event_generator():
        async for mode, data in compliance_agent.astream(
            initial_state, stream_mode=["custom", "updates"]
        ):
            

            if mode == "custom":
                yield f"data: {json.dumps({
                    'type': 'status',
                    'data': data
                }, default=_json_default)}\n\n"

                
            elif mode == "updates":
                yield f"data: {json.dumps({
                    'type': 'update',
                    'data': data
                }, default=_json_default)}\n\n"


        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/health")
async def health_check():
    return {"status": "ok"}
