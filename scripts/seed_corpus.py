#!/usr/bin/env python3
"""CLI: Seed the ST corpus into the LightRAG knowledge graph."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path so st_graphrag is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from st_graphrag.config import load_config
from st_graphrag.seed import seed_corpus


def main():
    parser = argparse.ArgumentParser(
        description="Seed the Simulation Theology corpus into the knowledge graph."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: auto-detect)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and format entries but don't insert into graph",
    )
    parser.add_argument(
        "--file",
        default=None,
        help='Seed only this specific file (e.g., "Gating Router.md")',
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    asyncio.run(seed_corpus(config=config, dry_run=args.dry_run, single_file=args.file))


if __name__ == "__main__":
    main()
