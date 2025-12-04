"""Authentication domain entities."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import String
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import func

from src.abstract import Entity
from src.abstract import StatusMixin
from src.utilities.enums import Language


class User(StatusMixin, Entity):
    """User entity for authentication.

    Attributes:
        pk: UUID primary key.
        email: Unique email address (identifier).
        first_name: User's first name.
        last_name: User's last name.
        avatar_url: Optional URL to user's avatar image.
        language: Preferred language from Language enum.
        is_staff: Flag indicating if user has staff privileges.
        join_date: Timestamp when user registered.
        last_login: Timestamp of last successful login.
    """

    # Override pk to use UUID instead of BigInteger
    pk: Mapped[uuid.UUID] = mapped_column(
        "id",
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # account Uniqueness
    email: Mapped[str] = mapped_column(String(255), unique=True)

    # Basic user information
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[Language] = mapped_column(Enum(Language), default=Language.EN)

    # User type flags
    is_staff: Mapped[bool] = mapped_column(default=False)

    # Timestamps (timezone-aware UTC)
    join_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"
