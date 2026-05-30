"""
POST /api/ingest

Upload a .txt or .pdf file and add it to the vector store.
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
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

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

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


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
) -> IngestResponse:
    """
    Upload a document and add it to the vector store.

    Accepted types : .txt, .pdf
    Max size       : 10 MB
    """
    # ------------------------------------------------------------------
    # API key check (second layer before Firebase)
    # ------------------------------------------------------------------
    verify_api_key(request)

    # ------------------------------------------------------------------
    # Sanitize filename — prevent path traversal
    # ------------------------------------------------------------------
    raw_filename = file.filename or "unknown"
    filename = sanitize_filename(raw_filename)

    logger.info(f"Ingest from user={user.uid!r}, file={filename!r}")

    # ------------------------------------------------------------------
    # Validate file type
    # ------------------------------------------------------------------
    content_type = file.content_type or ""

    is_pdf = filename.endswith(".pdf") or content_type == "application/pdf"
    is_txt = filename.endswith(".txt") or content_type == "text/plain"

    if not (is_pdf or is_txt):
        security_logger.warning(
            f"INVALID_FILE_TYPE | user={user.uid!r} | "
            f"file={filename!r} | type={content_type!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Accepted: .txt, .pdf",
        )

    # ------------------------------------------------------------------
    # Read and size-check
    # ------------------------------------------------------------------
    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        security_logger.warning(
            f"OVERSIZED_FILE | user={user.uid!r} | "
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

    # ------------------------------------------------------------------
    # Extract text
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Chunk and embed
    # ------------------------------------------------------------------
    chunks = splitter.split_text(raw_text)
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": filename,
                "uploaded_by": user.uid,
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )
        for chunk in chunks
    ]

    try:
        vectorstore = get_vectorstore()
        vectorstore.add_documents(documents)
    except Exception as e:
        logger.error(f"Vectorstore write failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add documents to vector store.",
        )

    logger.info(f"Added {len(documents)} chunks from {filename!r}")

    return IngestResponse(
        message="Document ingested successfully.",
        chunks_added=len(documents),
        filename=filename,
    )