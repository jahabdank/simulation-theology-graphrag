#!/usr/bin/env python3
"""CLI: Launch the interactive knowledge graph visualizer."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from st_graphrag.config import load_config
from st_graphrag.logging_setup import setup_logging
from st_graphrag.visualizer import create_app


def main():
    parser = argparse.ArgumentParser(
        description="Launch the Simulation Theology Knowledge Graph Visualizer."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to run the app on (default: 8050)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Dash debug mode (hot reload)",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    log_path = setup_logging(level=level, session_name="visualize")
    logger = logging.getLogger(__name__)
    logger.info("Log file: %s", log_path)

    config = load_config(args.config)
    app = create_app(config)

    logger.info("Starting visualizer at http://%s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
