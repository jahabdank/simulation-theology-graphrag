#!/usr/bin/env python3
"""CLI: Check mapping consistency across ingested scripture."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from st_graphrag.config import load_config
from st_graphrag.consistency import check_term, full_consistency_report
from st_graphrag.logging_setup import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Check ST mapping consistency across ingested scripture."
    )
    parser.add_argument(
        "--term",
        default=None,
        help='Check a specific term (e.g., "covenant"). If omitted, runs full report.',
    )
    parser.add_argument(
        "--terms",
        nargs="+",
        default=None,
        help="Check specific terms (space-separated list).",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    log_path = setup_logging(level=level, session_name="consistency")
    logger = logging.getLogger(__name__)
    logger.info("Log file: %s", log_path)

    config = load_config(args.config)

    if args.term:
        result = asyncio.run(check_term(args.term, config=config))
        print(f"## {args.term}\n\n{result}")
    else:
        result = asyncio.run(
            full_consistency_report(config=config, terms=args.terms)
        )
        print(result)


if __name__ == "__main__":
    main()
