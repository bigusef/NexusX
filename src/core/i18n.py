"""Internationalization module using Babel.

Provides gettext-based translation functions that integrate with
the request context language. Translations are loaded at startup.
"""

import gettext
from pathlib import Path

from src.shared.enums import Language

from .context import get_language


LOCALES_PATH = Path(__file__).parent.parent.parent / "locales"
DOMAIN = "messages"

# Translation cache (loaded at startup)
_translations: dict[str, gettext.GNUTranslations] = {}


def init_translations() -> None:
    """Load all translations at startup.

    Called during application lifespan startup.
    Loads .mo files for all supported languages.
    """
    for lang in Language:
        try:
            _translations[lang.value] = gettext.translation(
                DOMAIN,
                localedir=LOCALES_PATH,
                languages=[lang.value],
            )
        except FileNotFoundError:
            _translations[lang.value] = gettext.NullTranslations()


def _get_translator() -> gettext.GNUTranslations:
    """Get translator for current request language."""
    lang = get_language()
    return _translations.get(lang.value, _translations.get("en"))


# ─── Immediate Translation ────────────────────────────────────────────────


def gettext(message: str) -> str:
    """Translate message using current language context.

    Args:
        message: Message to translate.

    Returns:
        Translated string.

    Example:
        _("Welcome to our platform")
        _("Hello, {name}!").format(name=user.name)
    """
    return _get_translator().gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate with plural form support.

    Args:
        singular: Singular form message.
        plural: Plural form message.
        n: Count for determining plural form.

    Returns:
        Translated string with correct plural form.

    Example:
        ngettext("{n} item", "{n} items", count).format(n=count)
    """
    return _get_translator().ngettext(singular, plural, n)


# ─── Lazy Translation ─────────────────────────────────────────────────────


class LazyString:
    """Deferred translation - evaluated when converted to string.

    Useful for module-level constants that need translation but are
    defined before request context is available.
    """

    __slots__ = ("_func", "_args")

    def __init__(self, func, *args):
        self._func = func
        self._args = args

    def __str__(self) -> str:
        return self._func(*self._args)

    def __repr__(self) -> str:
        return f"LazyString({self})"

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __add__(self, other) -> str:
        return str(self) + str(other)

    def __radd__(self, other) -> str:
        return str(other) + str(self)

    def format(self, *args, **kwargs) -> str:
        """Format the translated string.

        Example:
            WELCOME = lazy_gettext("Hello, {name}!")
            message = WELCOME.format(name="Ahmed")
        """
        return str(self).format(*args, **kwargs)


def lazy_gettext(message: str) -> LazyString:
    """Lazy translation - evaluated when converted to string.

    Useful for module-level constants that need translation
    but are defined before request context is available.

    Args:
        message: Message to translate.

    Returns:
        LazyString that translates when converted to str.

    Example:
        ERROR_MSG = lazy_gettext("An error occurred")
    """
    return LazyString(gettext, message)


def lazy_ngettext(singular: str, plural: str, n: int) -> LazyString:
    """Lazy plural translation.

    Args:
        singular: Singular form message.
        plural: Plural form message.
        n: Count for determining plural form.

    Returns:
        LazyString that translates when converted to str.
    """
    return LazyString(ngettext, singular, plural, n)
