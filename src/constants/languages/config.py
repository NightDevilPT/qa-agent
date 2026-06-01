"""
Central Registry for Language Configurations.
All nodes should import `get_language_config` from this file.
"""

from typing import Dict, Any
from .javascript import JAVASCRIPT_CONFIG
from .typescript import TYPESCRIPT_CONFIG

# ==========================================
# THE REGISTRY
# Strictly limited to JavaScript and TypeScript
# ==========================================
LANGUAGE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "javascript": JAVASCRIPT_CONFIG,
    "typescript": TYPESCRIPT_CONFIG,
}

def get_language_config(language: str) -> Dict[str, Any]:
    """
    Retrieve the configuration profile for a specific language.
    Handles aliases (e.g., 'js' -> 'javascript').
    Raises a ValueError if the language is not supported.
    """
    if not language:
        raise ValueError("Language parameter cannot be empty. Must be 'javascript' or 'typescript'.")

    normalized_lang = language.strip().lower()
    
    # Map common abbreviations to the official registry key
    aliases = {
        "js": "javascript",
        "ts": "typescript"
    }
    
    # Resolve alias if it exists, otherwise use the input
    resolved_lang = aliases.get(normalized_lang, normalized_lang)

    if resolved_lang not in LANGUAGE_REGISTRY:
        supported = ", ".join(LANGUAGE_REGISTRY.keys())
        raise ValueError(
            f"Unsupported language: '{language}'. "
            f"Currently, this agent strictly supports: {supported}"
        )
        
    return LANGUAGE_REGISTRY[resolved_lang]

def get_supported_languages() -> list[str]:
    """Returns a list of all currently supported languages."""
    return list(LANGUAGE_REGISTRY.keys())