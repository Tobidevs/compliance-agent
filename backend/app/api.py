import shutil
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from agent.utils.policy_rag_service import PolicyRAGService

router = APIRouter()
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
policy_service = PolicyRAGService(persist_directory=CHROMA_PERSIST_DIRECTORY)


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

        with tempfile.NamedTemporaryFile(prefix="policy_", suffix=suffix, delete=False) as temp_file:
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


@router.get("/health")
async def health_check():
    return {"status": "ok"}
