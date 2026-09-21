import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from .knowledge import knowledge_base
from .models.schemas import UploadResponse
from .auth import get_current_identity, check_permission, IdentityContext

logger = logging.getLogger("knoquest.upload")
upload_router = APIRouter(prefix="/api", tags=["Upload"])

UPLOAD_TMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "temp_uploads"))
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)

@upload_router.post("/upload", response_model=UploadResponse)
async def upload_document_endpoint(
    file: UploadFile = File(...),
    identity: IdentityContext = Depends(get_current_identity)
):
    """
    Accepts user-uploaded enterprise document (PDF, DOCX, TXT)
    and indexes it into the session knowledge base for instant grounded Q&A.
    Requires documents.read permission.
    """
    if not check_permission(identity, "documents.read"):
        raise HTTPException(status_code=403, detail="Permission denied: 'documents.read' required.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".txt", ".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'. Use PDF, DOCX, or TXT.")

    file_id = f"doc_{uuid.uuid4().hex[:8]}"
    saved_path = os.path.join(UPLOAD_TMP_DIR, f"{file_id}_{filename}")

    try:
        content_bytes = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content_bytes)

        # Extract text based on file format
        text_content = ""
        if ext == ".txt":
            text_content = content_bytes.decode("utf-8", errors="ignore")
        elif ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(saved_path)
            text_content = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == ".docx":
            import docx
            doc = docx.Document(saved_path)
            text_content = "\n".join([p.text for p in doc.paragraphs])

        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Document appears empty or unreadable.")

        # Index into knowledge base for session
        knowledge_base.add_session_document(
            session_file_id=file_id,
            filename=filename,
            content=text_content
        )

        chunks_count = len(knowledge_base.session_chunks.get(file_id, []))

        return UploadResponse(
            file_id=file_id,
            filename=filename,
            chunks_count=chunks_count,
            message=f"Document '{filename}' successfully parsed and indexed into {chunks_count} semantic chunks."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling file upload {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
