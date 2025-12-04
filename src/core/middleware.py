"""Request middleware module.

Provides middleware for request header validation and context injection.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response

from src.utilities.enums import Language
from src.utilities.enums import Platform

from .context import set_language
from .context import set_platform


# Paths excluded from X-Source validation
EXCLUDED_PATHS = frozenset({"/", "/health", "/openapi.json"})


class RequestHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to validate request headers and inject context.

    Validates:
        - Accept-Language: Optional, defaults to English if missing/invalid
        - X-Source: Required, must be 'admin' or 'customer'

    Sets context variables accessible via get_language() and get_platform().

    Excluded paths (no validation required):
        - / (Swagger UI)
        - /health
        - /openapi.json
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate headers.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from next handler or error response.
        """
        # Skip validation for excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Parse Accept-Language (optional, default EN)
        lang_header = request.headers.get("Accept-Language", "en")
        language = Language.from_code(lang_header)
        set_language(language)

        # Validate X-Source (required)
        source_header = request.headers.get("X-Source")
        if not source_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden Request"},
            )

        # Validate platform value
        source_lower = source_header.lower()
        if source_lower not in Platform.values():
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden Request"},
            )

        set_platform(Platform(source_lower))

        return await call_next(request)
