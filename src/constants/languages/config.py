"""
Language Configuration Hub
============================

Central config that loads all language definitions.
Add new language configs from their respective files.
"""

from typing import Dict, List, Any
from constants.languages.javascript import JAVASCRIPT_CONFIG
from constants.languages.typescript import TYPESCRIPT_CONFIG

DEFAULT_LANGUAGE = "typescript"

SUPPORTED_LANGUAGES: List[str] = ["typescript", "javascript"]

LANGUAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "typescript": TYPESCRIPT_CONFIG,
    "javascript": JAVASCRIPT_CONFIG,
}


def get_language_config(language: str) -> Dict[str, Any]:
    """Get configuration for a specific language."""
    if language not in LANGUAGE_CONFIG:
        raise ValueError(f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}")
    return LANGUAGE_CONFIG[language]


def detect_language(file_path: str) -> str:
    """Detect language from file extension."""
    from pathlib import Path

    ext = Path(file_path).suffix.lower()
    for lang, config in LANGUAGE_CONFIG.items():
        if ext in config.get("extensions", []):
            return lang
    raise ValueError(f"Unsupported file extension: {ext}")