"""
LLM provider abstraction supporting OpenAI, Anthropic, and Google.
Provides unified interface for generating text and embeddings.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from config import settings
from observability import trace_logger


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from message history."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.generate_with_messages(messages, temperature, max_tokens)

    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from message history."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            trace_logger.error_occurred(
                error_type="llm_generation_error",
                error_message=str(e),
                context={"provider": "openai", "model": self.model}
            )
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            trace_logger.error_occurred(
                error_type="llm_generation_error",
                error_message=str(e),
                context={"provider": "anthropic", "model": self.model}
            )
            raise

    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from message history."""
        # Extract system prompt if present
        system_prompt = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=user_messages
            )
            return response.content[0].text
        except Exception as e:
            trace_logger.error_occurred(
                error_type="llm_generation_error",
                error_message=str(e),
                context={"provider": "anthropic", "model": self.model}
            )
            raise


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self):
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.llm_model)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            return response.text
        except Exception as e:
            trace_logger.error_occurred(
                error_type="llm_generation_error",
                error_message=str(e),
                context={"provider": "google", "model": settings.llm_model}
            )
            raise

    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from message history."""
        # Convert messages to Gemini format
        chat = self.model.start_chat(history=[])

        system_prompt = None
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
                continue

            # Convert role names
            role = "user" if msg["role"] in ["user", "human"] else "model"

            if role == "user":
                response = chat.send_message(
                    msg["content"],
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                )

        return response.text if response else ""


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI embeddings provider."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            trace_logger.error_occurred(
                error_type="embedding_error",
                error_message=str(e),
                context={"provider": "openai", "model": self.model}
            )
            raise


def get_llm_provider() -> LLMProvider:
    """Factory function to get configured LLM provider."""
    provider_map = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider
    }

    provider_class = provider_map.get(settings.llm_provider)
    if not provider_class:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    return provider_class()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function to get configured embedding provider."""
    # For now, only OpenAI embeddings supported
    # Can extend to other providers as needed
    if settings.embedding_provider == "openai":
        return OpenAIEmbedding()
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
