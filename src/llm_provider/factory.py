"""LLM Provider Factory.

Factory class to instantiate and retrieve concrete LLM provider instances
('docker', 'gemini', 'openai').
"""

import os
from typing import Any, Dict, Type
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

from src.llm_provider.providers.base_provider import BaseLLMProvider
from src.llm_provider.providers.docker_provider import DockerLLMProvider
from src.llm_provider.providers.gemini_provider import GeminiLLMProvider
from src.llm_provider.providers.openai_provider import OpenAILLMProvider


class LLMProviderFactory:
    """Factory class for instantiating LLM Providers."""

    _PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
        "docker": DockerLLMProvider,
        "gemini": GeminiLLMProvider,
        "openai": OpenAILLMProvider,
    }

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[BaseLLMProvider]) -> None:
        """Register a custom LLM provider class."""
        cls._PROVIDERS[provider_name.lower()] = provider_class

    @classmethod
    def create_provider(cls, provider_type: str = "docker", **kwargs: Any) -> BaseLLMProvider:
        """Create and return an instance of the requested LLM Provider.

        Args:
            provider_type: Provider key string ('docker', 'gemini', 'openai').
            **kwargs: Extra parameters passed to the provider constructor.

        Returns:
            Instance of BaseLLMProvider.
        """
        selected_type = (
            provider_type
            or os.getenv("LLM_PROVIDER")
            or "docker"
        ).lower()

        provider_cls = cls._PROVIDERS.get(selected_type)
        if not provider_cls:
            valid_keys = list(cls._PROVIDERS.keys())
            raise ValueError(
                f"Unknown LLM provider type '{selected_type}'. Valid providers are: {valid_keys}"
            )

        return provider_cls(**kwargs)
