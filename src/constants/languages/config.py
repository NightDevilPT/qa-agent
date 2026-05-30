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
    """Get configuration for a selected language."""
    if language not in LANGUAGE_CONFIG:
        raise ValueError(f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}")
    return LANGUAGE_CONFIG[language]


def normalize_project_language(value: str) -> str:
    """Map user input (js, ts, javascript, ...) to registry key."""
    key = value.strip().lower()
    aliases = {
        "js": "javascript",
        "jsx": "javascript",
        "javascript": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
        "typescript": "typescript",
    }
    if key not in aliases:
        raise ValueError(
            f"Unsupported project language: {value!r}. "
            f"Use one of: javascript, typescript (or js, ts)."
        )
    return aliases[key]


def get_all_exclude_patterns() -> List[str]:
    """Merged exclude patterns from all language configs (deduplicated)."""
    patterns: List[str] = []
    seen: set[str] = set()
    for config in LANGUAGE_CONFIG.values():
        for pattern in config.get("exclude_patterns", []):
            if pattern not in seen:
                seen.add(pattern)
                patterns.append(pattern)
    return patterns


def get_extensions_for_language(language: str) -> tuple[str, ...]:
    """File extensions for the selected project language only."""
    config = get_language_config(normalize_project_language(language))
    return tuple(config.get("extensions", []))


def detect_language(file_path: str) -> str:
    """Detect language from file extension."""
    from pathlib import Path
    
    ext = Path(file_path).suffix.lower()
    for lang, config in LANGUAGE_CONFIG.items():
        if ext in config.get("extensions", []):
            return lang
    raise ValueError(f"Unsupported file extension: {ext}")