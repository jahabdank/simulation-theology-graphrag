"""Shared test fixtures for st_graphrag tests."""

import sys
from pathlib import Path

import pytest

# Ensure st_graphrag is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def corpus_dir():
    """Path to the actual corpus directory."""
    path = Path(__file__).parent.parent.parent / "simulation-theology-corpus" / "corpus"
    if not path.exists():
        pytest.skip("Corpus directory not available")
    return path


@pytest.fixture
def sample_corpus_file(corpus_dir):
    """Path to a known corpus file for testing."""
    path = corpus_dir / "Gating Router.md"
    if not path.exists():
        pytest.skip("Gating Router.md not found in corpus")
    return path
