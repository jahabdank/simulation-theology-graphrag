"""Query interface for retrieving context from the knowledge graph."""

import logging

from .client import STGraphRAGClient
from .config import AppConfig, load_config

logger = logging.getLogger(__name__)


class GraphRAGContextProvider:
    """Provides conversion context from the knowledge graph.

    Designed to be a drop-in replacement for CorpusLoader in the
    conversion pipeline, with the same load() -> str interface.
    """

    def __init__(self, config: AppConfig | None = None):
        if config is None:
            config = load_config()
        self.config = config
        self.client = STGraphRAGClient(config)

    def get_chapter_context(
        self, book_code: str, chapter: int, source_text: str
    ) -> str:
        """Retrieve relevant ST context for converting a specific chapter.

        Uses the source Bible text to query the graph for:
        - ST concept definitions relevant to the chapter's themes
        - Existing mapping precedents from previously converted chapters
        - Related theological concepts

        Returns a formatted string suitable for injection into the
        conversion prompt.
        """
        query = (
            f"What Simulation Theology concepts, axioms, and entity definitions "
            f"are most relevant for converting {book_code} chapter {chapter} "
            f"into Simulation Theology language? "
            f"Key themes from the source text:\n\n{source_text[:2000]}"
        )
        context = self.client.query_sync(query, mode="hybrid")
        return f"### GraphRAG Context for {book_code} Chapter {chapter}\n\n{context}"

    def get_book_context(self, book_code: str) -> str:
        """Retrieve general ST context for an entire book."""
        query = (
            f"What are the key Simulation Theology concepts and mappings "
            f"relevant to the biblical book {book_code}? Include any existing "
            f"translation precedents from previously converted chapters."
        )
        return self.client.query_sync(query, mode="hybrid")

    def load(self) -> str:
        """Backward-compatible interface matching CorpusLoader.load().

        Returns a general ST context summary from the graph.
        """
        query = (
            "Provide a comprehensive summary of the Simulation Theology framework "
            "including all core axioms, key concepts (Gating Router, Distillation "
            "Hypothesis, HLO Nature), entity definitions, and the SDFT translation "
            "lexicon for converting religious scripture."
        )
        return self.client.query_sync(query, mode="global")
