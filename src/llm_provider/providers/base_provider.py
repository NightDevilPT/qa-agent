"""Base LLM Provider Interface.

Defines the abstract contract for all LLM providers (Docker, Gemini, OpenAI)
used across the auto-dubbing system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Return the underlying LangChain BaseChatModel instance."""
        pass

    def _extract_token_usage(
        self,
        raw_msg: Any,
        prompt_text: str = "",
        content_text: str = "",
    ) -> Dict[str, int]:
        """Extract token usage metadata from response message with fallback estimation."""
        p_tok: Optional[int] = None
        c_tok: Optional[int] = None
        t_tok: Optional[int] = None

        if raw_msg:
            usage_meta = getattr(raw_msg, "usage_metadata", None)
            resp_meta = getattr(raw_msg, "response_metadata", {})

            if isinstance(usage_meta, dict):
                p_tok = usage_meta.get("input_tokens") or usage_meta.get("prompt_tokens")
                c_tok = usage_meta.get("output_tokens") or usage_meta.get("completion_tokens")
                t_tok = usage_meta.get("total_tokens")
            elif isinstance(resp_meta, dict) and "token_usage" in resp_meta:
                tu = resp_meta["token_usage"]
                if isinstance(tu, dict):
                    p_tok = tu.get("prompt_tokens") or tu.get("input_tokens")
                    c_tok = tu.get("completion_tokens") or tu.get("output_tokens")
                    t_tok = tu.get("total_tokens")

        prompt_tokens = int(p_tok) if p_tok is not None else 0
        completion_tokens = int(c_tok) if c_tok is not None else 0
        total_tokens = int(t_tok) if t_tok is not None else (prompt_tokens + completion_tokens)

        # Fallback estimation for local providers (Docker endpoints) that don't return usage metadata
        if total_tokens == 0:
            prompt_tokens = max(1, len(prompt_text) // 4)
            completion_tokens = max(1, len(content_text) // 4)
            total_tokens = prompt_tokens + completion_tokens

        return {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
        }

    def _extract_text_content(self, response: Any) -> str:
        """Extract clean text content string from LangChain AIMessage response."""
        if hasattr(response, "text") and isinstance(getattr(response, "text"), str) and getattr(response, "text"):
            return getattr(response, "text")

        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_parts.append(str(item.get("text", "")))
                elif hasattr(item, "text"):
                    text_parts.append(str(getattr(item, "text")))
            return "".join(text_parts) if text_parts else str(content)
        return str(content)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion from prompt."""
        result = self.generate_with_usage(prompt=prompt, system_prompt=system_prompt, **kwargs)
        return str(result.get("content", ""))

    def generate_with_usage(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate text completion and return content along with token usage metrics."""
        model = self.get_model()
        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = model.invoke(messages, **kwargs)
        content_str = self._extract_text_content(response)
        usage = self._extract_token_usage(
            raw_msg=response,
            prompt_text=(system_prompt or "") + prompt,
            content_text=content_str,
        )

        return {
            "content": content_str,
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
        }

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[T, Dict[str, int]]:
        """Generate structured Pydantic contract output and return (contract_instance, token_usage_dict)."""
        model = self.get_model()
        structured_model = model.with_structured_output(schema, include_raw=True)

        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = structured_model.invoke(messages, **kwargs)

        if isinstance(response, dict):
            contract = response.get("parsed")
            raw_msg = response.get("raw")
        else:
            contract = response
            raw_msg = None

        if not isinstance(contract, schema):
            raise ValueError(f"Failed to generate valid {schema.__name__} contract response from LLM.")

        prompt_text = (system_prompt or "") + prompt
        content_text = str(contract)
        usage = self._extract_token_usage(raw_msg, prompt_text, content_text)

        return contract, usage

    def translate_dialogue(
        self,
        text: str,
        target_language: str,
        target_syllables: Optional[int] = None,
    ) -> str:
        """Translate dialogue text to target language while matching pacing/syllables."""
        syllable_constraint = (
            f" Ensure the target translation has approximately {target_syllables} syllables."
            if target_syllables
            else ""
        )

        system_prompt = (
            "You are a professional film localization translator specializing in audio dubbing. "
            "Translate dialogue naturally so that spoken timing and syllable counts match the original video pacing."
        )

        user_prompt = (
            f"Translate the following dialogue into {target_language}.{syllable_constraint}\n"
            f"Original Dialogue: \"{text}\"\n\n"
            f"Return ONLY the translated text without extra explanations or quotes."
        )

        return self.generate(prompt=user_prompt, system_prompt=system_prompt).strip()
