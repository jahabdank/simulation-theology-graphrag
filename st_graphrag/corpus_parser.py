"""Parse Simulation Theology corpus markdown files into structured entries."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


@dataclass
class CorpusEntry:
    title: str
    id: str
    type: str  # "axiom", "concept", "entity"
    related: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    content: str = ""  # markdown body (after frontmatter)
    filepath: Path = field(default_factory=lambda: Path())


def parse_corpus_file(path: Path) -> CorpusEntry:
    """Parse a single corpus .md file into a CorpusEntry."""
    text = path.read_text(encoding="utf-8")
    title = path.stem

    # Split frontmatter from body
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()

    # Extract wikilinks from body
    wikilinks = sorted(set(WIKILINK_PATTERN.findall(body)))

    return CorpusEntry(
        title=title,
        id=frontmatter.get("id", title),
        type=frontmatter.get("type", "concept"),
        related=frontmatter.get("related", []),
        wikilinks=wikilinks,
        content=body,
        filepath=path,
    )


def parse_all_corpus(corpus_dir: str | Path) -> list[CorpusEntry]:
    """Parse all .md files in the corpus directory."""
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    entries = []
    for path in sorted(corpus_dir.glob("*.md")):
        entries.append(parse_corpus_file(path))
    return entries


def format_for_lightrag(entry: CorpusEntry) -> str:
    """Format a corpus entry for LightRAG insertion.

    Includes a structured metadata header so LightRAG's entity extraction
    can identify the entry type and relationships.
    """
    related_str = ", ".join(entry.related) if entry.related else "(none)"

    return (
        f"[CORPUS ENTRY: {entry.title}]\n"
        f"Type: {entry.type} | ID: {entry.id}\n"
        f"Related concepts: {related_str}\n"
        f"\n"
        f"{entry.content}"
    )
