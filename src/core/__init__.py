"""Core infrastructure module"""

from .config import get_settings
from .context import get_language
from .context import get_platform
from .i18n import gettext
from .i18n import lazy_gettext
from .i18n import lazy_ngettext
from .i18n import ngettext
from .middleware import RequestHeadersMiddleware


settings = get_settings()

__all__ = [
    "settings",
    # Context functions
    "get_platform",
    "get_language",
    # Translation functions
    "gettext",
    "lazy_gettext",
    "ngettext",
    "lazy_ngettext",
]
