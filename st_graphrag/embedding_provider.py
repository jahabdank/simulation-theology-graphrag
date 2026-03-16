"""Local embedding provider using sentence-transformers."""

import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model(model_name: str):
    """Lazily load the sentence-transformers model (cached)."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def create_embedding_func(model_name: str = "all-MiniLM-L6-v2"):
    """Create an async embedding function for LightRAG.

    Returns a coroutine function with signature:
        async def embed(texts: list[str]) -> np.ndarray
    """

    async def embedding_func(texts: list[str]) -> np.ndarray:
        model = _get_model(model_name)
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings

    return embedding_func
