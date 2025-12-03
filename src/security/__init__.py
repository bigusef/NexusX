"""Security module for authentication and authorization.

This package provides cross-cutting security concerns:
- JWT token management (generation, verification, revocation)
- FastAPI dependencies for protected endpoints (UserID, StaffID)
"""

from .dependencies import StaffID
from .dependencies import UserID
from .jwt import JWTService
from .jwt import TokenPair


__all__ = [
    "JWTService",
    "TokenPair",
    "UserID",
    "StaffID",
]
