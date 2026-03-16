#!/usr/bin/env python3
"""CLI: Ingest a converted ST scripture chapter into the knowledge graph."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from st_graphrag.config import load_config
from st_graphrag.ingest import ingest_book, ingest_chapter
from st_graphrag.logging_setup import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Ingest converted ST scripture into the knowledge graph."
    )
    parser.add_argument(
        "--translation",
        required=True,
        help="Translation identifier (e.g., eng-engBBE)",
    )
    parser.add_argument(
        "--book",
        required=True,
        help="Book code (e.g., GEN, EXO, MAT)",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="Chapter number. If omitted, ingests the entire book.",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    log_path = setup_logging(level=level, session_name="ingest")
    logger = logging.getLogger(__name__)
    logger.info("Log file: %s", log_path)

    config = load_config(args.config)

    if args.chapter is not None:
        asyncio.run(
            ingest_chapter(args.translation, args.book, args.chapter, config=config)
        )
    else:
        asyncio.run(ingest_book(args.translation, args.book, config=config))


if __name__ == "__main__":
    main()
