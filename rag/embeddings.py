"""
Embedding generation with caching.
"""

from typing import List, Dict, Any
import hashlib
import json
from pathlib import Path

from integrations import get_embedding_provider
from observability import trace_logger


class EmbeddingCache:
    """Simple file-based cache for embeddings."""

    def __init__(self, cache_dir: str = "./data/embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> List[float] | None:
        """Get cached embedding."""
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                trace_logger.warning(
                    "Failed to load cached embedding",
                    error=str(e),
                    cache_key=cache_key
                )
        return None

    def set(self, text: str, embedding: List[float]):
        """Cache embedding."""
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w") as f:
                json.dump(embedding, f)
        except Exception as e:
            trace_logger.warning(
                "Failed to cache embedding",
                error=str(e),
                cache_key=cache_key
            )


class EmbeddingGenerator:
    """Generates embeddings with caching."""

    def __init__(self, use_cache: bool = True):
        self.provider = get_embedding_provider()
        self.cache = EmbeddingCache() if use_cache else None

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Uses cache to avoid redundant API calls.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        embeddings = []
        texts_to_embed = []
        text_indices = []

        # Check cache
        for i, text in enumerate(texts):
            if self.cache:
                cached = self.cache.get(text)
                if cached:
                    embeddings.append((i, cached))
                    continue

            texts_to_embed.append(text)
            text_indices.append(i)

        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                new_embeddings = self.provider.embed(texts_to_embed)

                # Cache new embeddings
                if self.cache:
                    for text, embedding in zip(texts_to_embed, new_embeddings):
                        self.cache.set(text, embedding)

                # Add to results
                for idx, embedding in zip(text_indices, new_embeddings):
                    embeddings.append((idx, embedding))

            except Exception as e:
                trace_logger.error_occurred(
                    error_type="embedding_generation_failed",
                    error_message=str(e),
                    context={"num_texts": len(texts_to_embed)}
                )
                raise

        # Sort by original index
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text."""
        return self.embed([text])[0]
