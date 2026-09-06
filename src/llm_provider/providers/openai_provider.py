"""OpenAI LLM Provider Implementation."""

import os
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.llm_provider.providers.base_provider import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """Concrete LLM Provider for official OpenAI models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.3,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or "dummy-openai-key"
        self.model_name = model_name or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.temperature = temperature
        self._chat_model: Optional[ChatOpenAI] = None

    def get_model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = ChatOpenAI(
                openai_api_key=self.api_key,
                model=self.model_name,
                temperature=self.temperature,
            )
        return self._chat_model
