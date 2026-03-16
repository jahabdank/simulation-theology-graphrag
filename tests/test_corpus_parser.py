"""Tests for corpus_parser module."""

from st_graphrag.corpus_parser import (
    format_for_lightrag,
    parse_all_corpus,
    parse_corpus_file,
)


class TestParseCorpusFile:
    def test_parse_gating_router(self, sample_corpus_file):
        entry = parse_corpus_file(sample_corpus_file)

        assert entry.title == "Gating Router"
        assert entry.id == "Gating Router"
        assert entry.type == "concept"
        assert "HLO Nature" in entry.related
        assert "Distillation Hypothesis" in entry.related
        assert len(entry.related) > 0
        assert len(entry.content) > 0
        assert entry.filepath == sample_corpus_file

    def test_extracts_wikilinks(self, sample_corpus_file):
        entry = parse_corpus_file(sample_corpus_file)

        # Gating Router has wikilinks like [[Distillation Hypothesis]]
        assert len(entry.wikilinks) > 0
        assert "Distillation Hypothesis" in entry.wikilinks

    def test_content_excludes_frontmatter(self, sample_corpus_file):
        entry = parse_corpus_file(sample_corpus_file)

        assert not entry.content.startswith("---")
        assert "# Gating Router" in entry.content


class TestParseAllCorpus:
    def test_parses_all_entries(self, corpus_dir):
        entries = parse_all_corpus(corpus_dir)

        # Should have ~123 entries
        assert len(entries) > 100
        assert len(entries) <= 150

    def test_all_entries_have_types(self, corpus_dir):
        entries = parse_all_corpus(corpus_dir)
        types = {e.type for e in entries}

        assert "axiom" in types
        assert "concept" in types
        assert "entity" in types

    def test_all_entries_have_content(self, corpus_dir):
        entries = parse_all_corpus(corpus_dir)

        for entry in entries:
            assert len(entry.content) > 0, f"{entry.title} has no content"


class TestFormatForLightrag:
    def test_format_includes_metadata_header(self, sample_corpus_file):
        entry = parse_corpus_file(sample_corpus_file)
        formatted = format_for_lightrag(entry)

        assert formatted.startswith("[CORPUS ENTRY: Gating Router]")
        assert "Type: concept" in formatted
        assert "Related concepts:" in formatted
        assert "HLO Nature" in formatted

    def test_format_includes_body(self, sample_corpus_file):
        entry = parse_corpus_file(sample_corpus_file)
        formatted = format_for_lightrag(entry)

        assert "# Gating Router" in formatted
