"""LightRAG client — wires together LLM, embedding, and graph storage."""

import asyncio
import logging
from pathlib import Path

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

from .config import AppConfig, load_config
from .embedding_provider import create_embedding_func
from .entity_types import ST_ENTITY_TYPES
from .llm_provider import claude_code_llm, configure as configure_llm

logger = logging.getLogger(__name__)


class STGraphRAGClient:
    """High-level client for the Simulation Theology knowledge graph."""

    def __init__(self, config: AppConfig | None = None):
        if config is None:
            config = load_config()
        self.config = config

        # Configure the LLM provider
        configure_llm(config.claude)

        # Ensure working directory exists
        working_dir = Path(config.lightrag.working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        # Create the LightRAG instance
        self.rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=claude_code_llm,
            embedding_func=EmbeddingFunc(
                embedding_dim=config.embedding.embedding_dim,
                max_token_size=8192,
                func=create_embedding_func(config.embedding.model_name),
            ),
            chunk_token_size=config.lightrag.chunk_token_size,
            chunk_overlap_token_size=config.lightrag.chunk_overlap_token_size,
            entity_extract_max_gleaning=config.lightrag.entity_extract_max_gleaning,
            addon_params={"entity_types": ST_ENTITY_TYPES},
        )

    async def initialize(self) -> None:
        """Initialize storage backends (must be called before use)."""
        await self.rag.initialize_storages()
        logger.info("LightRAG storages initialized")

    async def finalize(self) -> None:
        """Flush and close storage backends."""
        await self.rag.finalize_storages()
        logger.info("LightRAG storages finalized")

    async def insert(self, text: str, doc_id: str | None = None) -> None:
        """Insert a document into the knowledge graph."""
        await self.rag.ainsert(text, ids=doc_id)

    async def query(self, question: str, mode: str | None = None) -> str:
        """Query the knowledge graph and return context text."""
        if mode is None:
            mode = self.config.lightrag.query.default_mode
        param = QueryParam(
            mode=mode,
            top_k=self.config.lightrag.query.top_k,
        )
        return await self.rag.aquery(question, param=param)

    async def delete(self, doc_ids: list[str]) -> None:
        """Delete documents from the knowledge graph."""
        await self.rag.adelete(doc_ids)

    # Synchronous convenience methods

    def insert_sync(self, text: str, doc_id: str | None = None) -> None:
        """Synchronous wrapper for insert."""
        asyncio.run(self._run_with_lifecycle(self.insert(text, doc_id=doc_id)))

    def query_sync(self, question: str, mode: str | None = None) -> str:
        """Synchronous wrapper for query."""
        return asyncio.run(self._run_with_lifecycle(self.query(question, mode=mode)))

    async def _run_with_lifecycle(self, coro):
        """Run a coroutine with storage init/finalize lifecycle."""
        await self.initialize()
        try:
            return await coro
        finally:
            await self.finalize()
