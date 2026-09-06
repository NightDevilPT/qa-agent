"""Docker LLM Provider Implementation."""

import os
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.llm_provider.providers.base_provider import BaseLLMProvider


class DockerLLMProvider(BaseLLMProvider):
    """Concrete LLM Provider for Docker-hosted OpenAI-compatible local models."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
    ):
        self.base_url = (
            base_url
            or os.getenv("DOCKER_LLM_BASE_URL")
            or "http://localhost:8000/v1"
        )
        self.model_name = (
            model_name
            or os.getenv("DOCKER_LLM_MODEL")
            or "qwen2.5:3b"
        )
        self.api_key = (
            api_key
            or os.getenv("DOCKER_LLM_API_KEY")
            or "docker"
        )
        self.temperature = temperature
        self._chat_model: Optional[ChatOpenAI] = None

    def get_model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = ChatOpenAI(
                openai_api_base=self.base_url,
                openai_api_key=self.api_key,
                model=self.model_name,
                temperature=self.temperature,
            )
        return self._chat_model
