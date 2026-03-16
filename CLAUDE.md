# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What This Is

A LightRAG-based GraphRAG service for the Simulation Theology project. It provides:
- **Knowledge graph** of ST corpus entries + converted scripture
- **Context retrieval** for the Bible-to-ST conversion pipeline
- **Consistency checking** for translation mappings across books

## Architecture

- **LLM**: Claude Code CLI (`claude -p`) via async wrapper — uses Max subscription
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`), local CPU
- **Graph**: NetworkX + NanoVectorDB (file-based, in `lightrag_data/`)
- **No external services required** — no Docker, no Neo4j, no API keys

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Seed the corpus (123 entries)
python scripts/seed_corpus.py
python scripts/seed_corpus.py --dry-run           # preview without inserting
python scripts/seed_corpus.py --file "Gating Router.md"  # single entry

# Ingest a converted chapter
python scripts/ingest_chapter.py --translation eng-engBBE --book GEN --chapter 1
python scripts/ingest_chapter.py --translation eng-engBBE --book GEN  # whole book

# Query the graph
python scripts/query_context.py "What ST concepts relate to salvation?"
python scripts/query_context.py "How is prayer mapped?" --mode local

# Check consistency
python scripts/check_consistency.py --term "covenant"
python scripts/check_consistency.py  # full report

# Run tests
python -m pytest tests/ -v
```

## Configuration

All settings in `config.yaml`:
- `claude.model` — which Claude model for extraction (default: opus)
- `embedding.model_name` — sentence-transformers model
- `lightrag.*` — LightRAG parameters (chunk size, query settings)
- `paths.*` — relative paths to sibling submodules

## Module Structure

| Module | Purpose |
|--------|---------|
| `st_graphrag/config.py` | Load config.yaml, resolve paths |
| `st_graphrag/entity_types.py` | Custom ST entity type definitions |
| `st_graphrag/corpus_parser.py` | Parse corpus .md files (YAML frontmatter + wikilinks) |
| `st_graphrag/llm_provider.py` | Claude Code CLI wrapper (async LLM function) |
| `st_graphrag/embedding_provider.py` | sentence-transformers wrapper |
| `st_graphrag/client.py` | LightRAG client (wires everything together) |
| `st_graphrag/seed.py` | Seed 123 corpus entries into graph |
| `st_graphrag/ingest.py` | Ingest converted ST scripture chapters |
| `st_graphrag/query.py` | Retrieve context for conversion pipeline |
| `st_graphrag/consistency.py` | Mapping drift detection |

## Integration with Conversion Pipeline

The `GraphRAGContextProvider` in `query.py` provides a `load() -> str` interface
compatible with the existing `CorpusLoader` in the pipeline. Future integration
adds a `graphrag` mode to `corpus_loader.py`.
