"""Seed the LightRAG knowledge graph with the ST corpus."""

import json
import logging
from pathlib import Path

from .config import AppConfig, load_config
from .corpus_parser import format_for_lightrag, parse_all_corpus

logger = logging.getLogger(__name__)

STATUS_FILENAME = "seed_status.json"


def _load_status(working_dir: str) -> dict:
    """Load the seed status file tracking which entries have been ingested."""
    status_path = Path(working_dir) / STATUS_FILENAME
    if status_path.exists():
        return json.loads(status_path.read_text())
    return {"seeded_files": []}


def _save_status(working_dir: str, status: dict) -> None:
    """Save the seed status file."""
    status_path = Path(working_dir) / STATUS_FILENAME
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2))


async def seed_corpus(
    config: AppConfig | None = None,
    dry_run: bool = False,
    single_file: str | None = None,
) -> None:
    """Seed all corpus entries into the LightRAG knowledge graph.

    Args:
        config: Application configuration. Loaded from config.yaml if None.
        dry_run: If True, parse and format entries but don't insert.
        single_file: If set, only seed this specific file (e.g., "Gating Router.md").
    """
    if config is None:
        config = load_config()

    entries = parse_all_corpus(config.paths.corpus_dir)
    logger.info("Parsed %d corpus entries from %s", len(entries), config.paths.corpus_dir)

    if single_file:
        entries = [e for e in entries if e.filepath.name == single_file]
        if not entries:
            logger.error("File not found in corpus: %s", single_file)
            return

    if dry_run:
        for entry in entries:
            formatted = format_for_lightrag(entry)
            print(f"\n{'='*60}")
            print(f"ENTRY: {entry.title} (type={entry.type})")
            print(f"Related: {entry.related}")
            print(f"Wikilinks: {entry.wikilinks}")
            print(f"Formatted length: {len(formatted)} chars")
            print(f"{'='*60}")
            print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        print(f"\nTotal: {len(entries)} entries (dry run, nothing inserted)")
        return

    # Deferred import — LightRAG not needed for dry-run
    from .client import STGraphRAGClient

    # Load status for resumability
    status = _load_status(config.lightrag.working_dir)
    already_seeded = set(status["seeded_files"])

    # Filter out already-seeded entries
    to_seed = [e for e in entries if e.filepath.name not in already_seeded]
    if not to_seed:
        logger.info("All %d entries already seeded. Nothing to do.", len(entries))
        return

    logger.info(
        "Seeding %d entries (%d already done, %d total)",
        len(to_seed),
        len(already_seeded),
        len(entries),
    )

    client = STGraphRAGClient(config)
    await client.initialize()

    try:
        for i, entry in enumerate(to_seed, 1):
            formatted = format_for_lightrag(entry)
            doc_id = f"corpus:{entry.filepath.name}"

            logger.info(
                "[%d/%d] Seeding: %s (type=%s, %d chars)",
                i,
                len(to_seed),
                entry.title,
                entry.type,
                len(formatted),
            )

            await client.insert(formatted, doc_id=doc_id)

            # Update status after each successful insert
            status["seeded_files"].append(entry.filepath.name)
            _save_status(config.lightrag.working_dir, status)

            logger.info("[%d/%d] Done: %s", i, len(to_seed), entry.title)
    finally:
        await client.finalize()

    logger.info("Seeding complete. %d entries in graph.", len(status["seeded_files"]))
