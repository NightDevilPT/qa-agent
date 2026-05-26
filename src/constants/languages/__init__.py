"""
Language Configuration
=======================

Provides language configs for all supported languages.
Extend by adding new files in this folder.

Usage:
    from constants.languages import get_language_config, detect_language, SUPPORTED_LANGUAGES
"""

from constants.languages.config import (
    LANGUAGE_CONFIG,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    get_language_config,
    detect_language,
)

__all__ = [
    "LANGUAGE_CONFIG",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "get_language_config",
    "detect_language",
]