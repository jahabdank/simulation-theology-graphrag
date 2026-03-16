"""Mapping drift detection — check consistency of term translations across chapters."""

import logging

from .client import STGraphRAGClient
from .config import AppConfig, load_config

logger = logging.getLogger(__name__)

KEY_RELIGIOUS_TERMS = [
    "God",
    "Lord",
    "salvation",
    "sin",
    "prayer",
    "faith",
    "soul",
    "heaven",
    "angels",
    "demons",
    "Holy Spirit",
    "covenant",
    "sacrifice",
    "temple",
    "prophecy",
    "grace",
    "repentance",
    "resurrection",
    "judgment",
    "mercy",
]


async def check_term(
    term: str,
    config: AppConfig | None = None,
) -> str:
    """Check how a specific religious term is mapped across all ingested chapters.

    Returns a text analysis of the term's translation consistency.
    """
    if config is None:
        config = load_config()

    client = STGraphRAGClient(config)
    await client.initialize()
    try:
        result = await client.query(
            f"How is the religious concept '{term}' translated into Simulation "
            f"Theology language across all ingested scripture chapters? "
            f"List all variations and note any inconsistencies.",
            mode="local",
        )
    finally:
        await client.finalize()

    return result


async def full_consistency_report(
    config: AppConfig | None = None,
    terms: list[str] | None = None,
) -> str:
    """Generate a comprehensive mapping consistency report.

    Checks all key religious terms (or a custom list) for translation
    consistency across the ingested scripture.
    """
    if config is None:
        config = load_config()
    if terms is None:
        terms = KEY_RELIGIOUS_TERMS

    client = STGraphRAGClient(config)
    await client.initialize()

    sections = []
    try:
        for term in terms:
            logger.info("Checking consistency for: %s", term)
            result = await client.query(
                f"How is '{term}' translated into Simulation Theology across all "
                f"ingested chapters? List variations and flag inconsistencies.",
                mode="local",
            )
            sections.append(f"## {term}\n\n{result}")
    finally:
        await client.finalize()

    header = (
        "# Simulation Theology Mapping Consistency Report\n\n"
        f"Terms checked: {len(terms)}\n\n---\n\n"
    )
    return header + "\n\n---\n\n".join(sections)
