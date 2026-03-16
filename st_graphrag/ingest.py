"""Ingest converted ST scripture chapters into the knowledge graph."""

import logging
import re
from pathlib import Path

from .client import STGraphRAGClient
from .config import AppConfig, load_config

logger = logging.getLogger(__name__)


def _find_sdf_file(sdf_dir: str, translation: str, book_code: str) -> Path | None:
    """Find the SDF output file for a given translation and book."""
    sdf_path = Path(sdf_dir)
    # Try common naming patterns
    patterns = [
        f"{translation}-{book_code}.txt",
        f"{translation}_{book_code}.txt",
        f"{book_code}.txt",
    ]
    for pattern in patterns:
        candidate = sdf_path / translation / pattern
        if candidate.exists():
            return candidate
        candidate = sdf_path / pattern
        if candidate.exists():
            return candidate

    # Glob fallback
    for match in sdf_path.rglob(f"*{book_code}*"):
        if match.is_file() and match.suffix == ".txt":
            return match

    return None


def _extract_chapter_verses(sdf_text: str, book_code: str, chapter: int) -> str:
    """Extract verses for a specific chapter from SDF text."""
    chapter_prefix = f"{book_code} {chapter}:"
    lines = []
    for line in sdf_text.splitlines():
        if line.strip().startswith(chapter_prefix):
            lines.append(line.strip())
    return "\n".join(lines)


def _format_chapter_for_lightrag(
    translation: str, book_code: str, chapter: int, verses: str
) -> str:
    """Format a chapter for LightRAG insertion."""
    return (
        f"[ST SCRIPTURE: {book_code} Chapter {chapter}]\n"
        f"Translation: {translation}\n"
        f"Book: {book_code}\n"
        f"Chapter: {chapter}\n"
        f"\n"
        f"{verses}"
    )


async def ingest_chapter(
    translation: str,
    book_code: str,
    chapter: int,
    config: AppConfig | None = None,
) -> None:
    """Ingest a single converted chapter into the knowledge graph."""
    if config is None:
        config = load_config()

    sdf_file = _find_sdf_file(config.paths.sdf_dir, translation, book_code)
    if sdf_file is None:
        logger.error(
            "SDF file not found for %s/%s in %s",
            translation,
            book_code,
            config.paths.sdf_dir,
        )
        return

    sdf_text = sdf_file.read_text(encoding="utf-8")
    verses = _extract_chapter_verses(sdf_text, book_code, chapter)

    if not verses:
        logger.error(
            "No verses found for %s chapter %d in %s", book_code, chapter, sdf_file
        )
        return

    formatted = _format_chapter_for_lightrag(translation, book_code, chapter, verses)
    doc_id = f"scripture:{translation}:{book_code}:{chapter}"

    logger.info(
        "Ingesting %s %s chapter %d (%d verses, %d chars)",
        translation,
        book_code,
        chapter,
        len(verses.splitlines()),
        len(formatted),
    )

    client = STGraphRAGClient(config)
    await client.initialize()
    try:
        await client.insert(formatted, doc_id=doc_id)
    finally:
        await client.finalize()

    logger.info("Ingested %s %s chapter %d", translation, book_code, chapter)


async def ingest_book(
    translation: str,
    book_code: str,
    config: AppConfig | None = None,
) -> None:
    """Ingest all chapters of a converted book."""
    if config is None:
        config = load_config()

    sdf_file = _find_sdf_file(config.paths.sdf_dir, translation, book_code)
    if sdf_file is None:
        logger.error(
            "SDF file not found for %s/%s in %s",
            translation,
            book_code,
            config.paths.sdf_dir,
        )
        return

    sdf_text = sdf_file.read_text(encoding="utf-8")

    # Discover chapters from the text
    chapter_pattern = re.compile(rf"^{re.escape(book_code)}\s+(\d+):", re.MULTILINE)
    chapters = sorted(set(int(m.group(1)) for m in chapter_pattern.finditer(sdf_text)))

    if not chapters:
        logger.error("No chapters found in %s", sdf_file)
        return

    logger.info(
        "Ingesting %s %s: %d chapters found (%d-%d)",
        translation,
        book_code,
        len(chapters),
        chapters[0],
        chapters[-1],
    )

    client = STGraphRAGClient(config)
    await client.initialize()
    try:
        for chapter in chapters:
            verses = _extract_chapter_verses(sdf_text, book_code, chapter)
            if not verses:
                continue
            formatted = _format_chapter_for_lightrag(
                translation, book_code, chapter, verses
            )
            doc_id = f"scripture:{translation}:{book_code}:{chapter}"
            logger.info("  Chapter %d (%d verses)", chapter, len(verses.splitlines()))
            await client.insert(formatted, doc_id=doc_id)
    finally:
        await client.finalize()

    logger.info("Ingested all %d chapters of %s %s", len(chapters), translation, book_code)
