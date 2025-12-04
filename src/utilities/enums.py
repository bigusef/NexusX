"""Shared enumeration module.

This module contains enumeration classes used across the application.
"""

from enum import StrEnum


class Environment(StrEnum):
    """Application environment enumeration.

    Defines the allowed runtime environments for the application.
    Used to control environment-specific behavior like debug mode.

    If an invalid or missing value is provided, defaults to DEVELOPMENT.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def _missing_(cls, value: object) -> "Environment":
        """Return default environment when value is invalid or missing.

        Args:
            value: The invalid value that was provided.

        Returns:
            DEVELOPMENT as the default environment.
        """
        return cls.DEVELOPMENT


class Language(StrEnum):
    """
    Supported languages in the application.

    Used for:
    - User preferences
    - Request language detection (Accept-Language header)
    - Content localization and i18n
    - API responses

    Language codes follow the ISO 639-1 standard (two-letter codes).
    """

    AR = "ar"  # Arabic
    DE = "de"  # German
    EN = "en"  # English
    ES = "es"  # Spanish
    FR = "fr"  # French
    RU = "ru"  # Russian
    IT = "it"  # Italian

    @classmethod
    def _missing_(cls, value: object) -> "Language":
        """
        Handle missing/invalid language codes.

        Called automatically when enum lookup fails (e.g., Language("invalid")).
        Returns the default language (English) instead of raising ValueError.

        Args:
            value: The value that failed to match

        Returns:
            Default language (English)

        Example:
            Language("en") → Language.EN
            Language("invalid") → Language.EN (via _missing_)
            Language("") → Language.EN (via _missing_)
            Language(None) → Language.EN (via _missing_)
        """
        return cls.EN

    @classmethod
    def from_code(cls, code: str) -> "Language":
        """
        Parse language from ISO 639-1 code.

        Args:
            code: Language code (e.g., "en", "ar", "en-US", "ar-SA")
                  Accepts both simple codes and locale codes

        Returns:
            Language enum, defaults to EN for invalid/empty codes.

        Example:
            Language.from_code("en") → Language.EN
            Language.from_code("en-US") → Language.EN
            Language.from_code("ar-SA") → Language.AR
            Language.from_code("xx") → Language.EN
        """
        if not code:
            return cls.EN

        # Extract primary language code (before hyphen if present)
        primary_code = code.lower().split("-")[0].strip()

        # Try to match with supported languages
        for lang in cls:
            if lang.value == primary_code:
                return lang

        return cls.EN

    @classmethod
    def values(cls) -> list[str]:
        """Get list of all supported language codes.

        Returns:
            List of ISO 639-1 codes.

        Example:
            Language.values()  # ["ar", "de", "en", "es", "fr", "ru", "it"]
        """
        return [lang.value for lang in cls]

    @property
    def display_name(self) -> str:
        """
        Return the human-readable name in the native language.

        Returns:
            Native language name
        """
        return {
            self.AR: "العربية",
            self.DE: "Deutsch",
            self.EN: "English",
            self.ES: "Español",
            self.FR: "Français",
            self.RU: "Русский",
            self.IT: "Italiano",
        }[self]


class Platform(StrEnum):
    """Request source/platform enumeration.

    Identifies the client platform making the request.
    Used for platform-specific logic and access control.

    Attributes:
        ADMIN: Dashboard for staff users
        CUSTOMER: Mobile app for regular users
    """

    ADMIN = "admin"
    CUSTOMER = "customer"

    @classmethod
    def values(cls) -> list[str]:
        """Get list of all platform values.

        Returns:
            List of platform string values.

        Example:
            Platform.values()  # ["admin", "customer"]
        """
        return [p.value for p in cls]
