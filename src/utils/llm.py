"""
Docker LLM Integration Utility
===============================

Connects to Docker-based LLM containers exposing OpenAI-compatible API.

Usage:
    from utils.llm import get_llm
    
    llm = get_llm(context=4)  # 4 * 1024 = 4096 tokens
    response = llm.invoke("Write a TypeScript function")
"""

import os
from langchain_openai import ChatOpenAI

# Configuration from environment
DOCKER_LLM_BASE_URL = os.getenv("DOCKER_LLM_BASE_URL", "http://localhost:12434/v1")
DOCKER_LLM_MODEL = os.getenv("DOCKER_LLM_MODEL", "ai/qwen2.5")
DOCKER_LLM_API_KEY = os.getenv("DOCKER_LLM_API_KEY", "not-needed")


def get_llm(
    context: int = 4,
    temperature: float = 0.1
) -> ChatOpenAI:
    """
    Create and return LangChain-compatible LLM client for Docker models.

    Parameters
    ----------
    context : int
        Context window size in multiples of 1024 tokens.
        4 = 4096, 8 = 8192, 16 = 16384. Default 4.
    temperature : float
        Response randomness. Lower = more deterministic. Default 0.1.

    Returns
    -------
    ChatOpenAI
        LangChain-compatible LLM client.

    Examples
    --------
    >>> llm = get_llm(context=8)  # 8192 tokens
    >>> response = llm.invoke("Write a Jest test for this function...")
    """
    return ChatOpenAI(
        model=DOCKER_LLM_MODEL,
        base_url=DOCKER_LLM_BASE_URL,
        api_key=DOCKER_LLM_API_KEY,
        temperature=temperature,
        max_tokens=context * 1024,
    )