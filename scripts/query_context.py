#!/usr/bin/env python3
"""CLI: Query the knowledge graph for relevant ST context."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from st_graphrag.client import STGraphRAGClient
from st_graphrag.config import load_config
from st_graphrag.logging_setup import setup_logging


async def run_query(question: str, mode: str, config_path: str | None):
    config = load_config(config_path)
    client = STGraphRAGClient(config)
    await client.initialize()
    try:
        result = await client.query(question, mode=mode)
        print(result)
    finally:
        await client.finalize()


def main():
    parser = argparse.ArgumentParser(
        description="Query the ST knowledge graph."
    )
    parser.add_argument(
        "question",
        help="The query to run against the knowledge graph",
    )
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["local", "global", "hybrid", "naive", "mix"],
        help="Query mode (default: hybrid)",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    log_path = setup_logging(level=level, session_name="query")
    logger = logging.getLogger(__name__)
    logger.info("Log file: %s", log_path)

    asyncio.run(run_query(args.question, args.mode, args.config))


if __name__ == "__main__":
    main()
