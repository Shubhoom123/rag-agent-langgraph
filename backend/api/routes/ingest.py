"""
POST /api/ingest

Upload a .txt or .pdf file and add it to the vector store.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from api.middleware.auth import AuthenticatedUser, get_current_user
from api.middleware.security import (
    sanitize_filename,
    verify_api_key,
    security_logger,
)
from api.models.schemas import IngestResponse
from api.providers import get_vectorstore

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_UPLOADS_PER_USER = 10

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)


def _extract_text_from_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def _extract_text_from_pdf(content: bytes) -> str:
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF support requires pypdf. Run: pip install pypdf",
        )


def _get_user_upload_count(namespace: str) -> int:
    """Get the number of uploads for a user from Firebase Firestore."""
    try:
        import firebase_admin
        from firebase_admin import firestore, credentials as fb_creds
        from api.config import settings

        if not firebase_admin._apps:
            if settings.firebase_credentials_path:
                cred = fb_creds.Certificate(settings.firebase_credentials_path)
            else:
                cred = fb_creds.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        doc = db.collection("user_uploads").document(namespace).get()
        if doc.exists:
            return doc.to_dict().get("upload_count", 0)
        return 0
    except Exception as e:
        logger.warning(f"Could not fetch upload count for {namespace}: {e}")
        return 0


def _increment_user_upload_count(namespace: str):
    """Increment the upload count for a user in Firebase Firestore."""
    try:
        import firebase_admin
        from firebase_admin import firestore, credentials as fb_creds
        from api.config import settings

        if not firebase_admin._apps:
            if settings.firebase_credentials_path:
                cred = fb_creds.Certificate(settings.firebase_credentials_path)
            else:
                cred = fb_creds.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        ref = db.collection("user_uploads").document(namespace)
        doc = ref.get()
        if doc.exists:
            ref.update({"upload_count": firestore.Increment(1)})
        else:
            ref.set({"upload_count": 1, "uid": namespace})
    except Exception as e:
        logger.warning(f"Could not increment upload count for {namespace}: {e}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> IngestResponse:
    verify_api_key(request)

    raw_filename = file.filename or "unknown"
    filename = sanitize_filename(raw_filename)

    namespace = user_id or user.uid
    logger.info(f"Ingest from user={namespace!r}, file={filename!r}")

    # Skip upload limit check for local dev
    if namespace != "local-dev":
        upload_count = _get_user_upload_count(namespace)
        if upload_count >= MAX_UPLOADS_PER_USER:
            security_logger.warning(
                f"UPLOAD_LIMIT_EXCEEDED | user={namespace!r} | count={upload_count}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Upload limit reached. Maximum {MAX_UPLOADS_PER_USER} documents per user.",
            )

    content_type = file.content_type or ""
    is_pdf = filename.endswith(".pdf") or content_type == "application/pdf"
    is_txt = filename.endswith(".txt") or content_type == "text/plain"

    if not (is_pdf or is_txt):
        security_logger.warning(
            f"INVALID_FILE_TYPE | user={namespace!r} | "
            f"file={filename!r} | type={content_type!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Accepted: .txt, .pdf",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        security_logger.warning(
            f"OVERSIZED_FILE | user={namespace!r} | "
            f"file={filename!r} | size={len(content)}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    try:
        raw_text = (
            _extract_text_from_pdf(content)
            if is_pdf
            else _extract_text_from_txt(content)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract text from file: {e}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text content found in the uploaded file.",
        )

    chunks = splitter.split_text(raw_text)
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": filename,
                "uploaded_by": namespace,
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )
        for chunk in chunks
    ]

    try:
        vectorstore = get_vectorstore()
        vectorstore.add_documents(documents, namespace=namespace)
    except Exception as e:
        logger.error(f"Vectorstore write failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add documents to vector store.",
        )

    # Increment upload count after successful ingest
    if namespace != "local-dev":
        _increment_user_upload_count(namespace)

    logger.info(f"Added {len(documents)} chunks from {filename!r} to namespace={namespace!r}")

    return IngestResponse(
        message="Document ingested successfully.",
        chunks_added=len(documents),
        filename=filename,
    )