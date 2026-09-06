"""Gemini LLM Provider Implementation."""

import os
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.llm_provider.providers.base_provider import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    """Concrete LLM Provider for Google Gemini models using native ChatGoogleGenerativeAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.3,
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or "dummy-gemini-key"
        )
        self.model_name = model_name or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
        self.temperature = temperature
        self._chat_model: Optional[ChatGoogleGenerativeAI] = None

    def get_model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=self.temperature,
            )
        return self._chat_model
