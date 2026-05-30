"""
Security middleware.

- Rate limiting via slowapi
- Security headers
- Request size limiting
- Basic prompt injection detection
- Security event logging
- Request ID tracking
- Filename sanitization
- API key authentication
"""
import logging
import logging.handlers
import os
import re
import uuid
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.config import settings

# ---------------------------------------------------------------------------
# Security Logger — writes to logs/security.log separately from app logs
# ---------------------------------------------------------------------------
def setup_security_logger() -> logging.Logger:
    """Set up a dedicated logger for security events."""
    os.makedirs(settings.log_dir, exist_ok=True)

    sec_logger = logging.getLogger("security")
    sec_logger.setLevel(logging.WARNING)

    # Rotating file handler — 5MB per file, keep 5 backups
    handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(settings.log_dir, "security.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))

    sec_logger.addHandler(handler)
    return sec_logger


security_logger = setup_security_logger()
app_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Request size limit
# ---------------------------------------------------------------------------
MAX_BODY_SIZE = 1 * 1024 * 1024  # 1MB


async def limit_request_size(request: Request, call_next: Callable) -> Response:
    """Reject requests with bodies larger than MAX_BODY_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        security_logger.warning(
            f"OVERSIZED_REQUEST | ip={request.client.host} | "
            f"path={request.url.path} | size={content_length}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request body too large. Maximum size is 1MB.",
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID tracking
# Every request gets a unique ID injected into headers and logs
# ---------------------------------------------------------------------------
async def add_request_id(request: Request, call_next: Callable) -> Response:
    """Attach a unique request ID to every request and response."""
    request_id = str(uuid.uuid4())

    # Store on request state so routes can access it
    request.state.request_id = request_id

    response = await call_next(request)

    # Return it in response header so frontend can log it for debugging
    response.headers["X-Request-ID"] = request_id

    return response


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """Add security headers to every response."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    # Remove server fingerprinting
    if "server" in response.headers:
        del response.headers["server"]

    return response


# ---------------------------------------------------------------------------
# API Key Authentication
# Simple second layer — check X-API-Key header
# ---------------------------------------------------------------------------
def verify_api_key(request: Request) -> None:
    """
    Verify the X-API-Key header if REQUIRE_API_KEY=true.

    Usage in routes:
        from api.middleware.security import verify_api_key
        ...
        verify_api_key(request)
    """
    if not settings.require_api_key:
        return

    api_key = request.headers.get("X-API-Key", "")

    if not api_key:
        security_logger.warning(
            f"MISSING_API_KEY | ip={request.client.host} | "
            f"path={request.url.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(api_key, settings.api_key):
        security_logger.warning(
            f"INVALID_API_KEY | ip={request.client.host} | "
            f"path={request.url.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )


# ---------------------------------------------------------------------------
# Filename sanitization
# Prevents path traversal attacks like ../../etc/passwd
# ---------------------------------------------------------------------------
SAFE_FILENAME_RE = re.compile(r"^[\w\-. ]+$")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent path traversal attacks.

    Raises HTTPException if filename is unsafe.
    """
    if not filename or filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename cannot be empty.",
        )

    # Strip directory components — never allow path separators
    basename = os.path.basename(filename)

    # Check for path traversal attempts
    if basename != filename.replace("\\", "/").split("/")[-1]:
        security_logger.warning(
            f"PATH_TRAVERSAL_ATTEMPT | filename={filename!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    # Only allow safe characters
    if not SAFE_FILENAME_RE.match(basename):
        security_logger.warning(
            f"UNSAFE_FILENAME | filename={filename!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters. "
                   "Use only letters, numbers, hyphens, underscores, and dots.",
        )

    # Enforce max length
    if len(basename) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename too long. Maximum 255 characters.",
        )

    return basename


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(if\s+you\s+are|a)",
    r"forget\s+(all\s+)?(previous|prior|your)\s+instructions",
    r"system\s*:\s*you\s+are",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*instruction",
]

COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
]


def sanitize_question(question: str) -> str:
    """
    Validate and sanitize a user question.
    Raises HTTPException if injection is detected.
    """
    question = question.strip()

    if len(question) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question too long. Maximum 1000 characters.",
        )

    for pattern in COMPILED_PATTERNS:
        if pattern.search(question):
            security_logger.warning(
                f"PROMPT_INJECTION | question={question[:100]!r}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input detected.",
            )

    return question