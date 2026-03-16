"""Load and resolve configuration from config.yaml."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ClaudeConfig:
    model: str = "opus"
    max_turns: int = 1
    timeout: int = 120
    max_concurrent: int = 2


@dataclass
class EmbeddingConfig:
    model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384


@dataclass
class QueryConfig:
    default_mode: str = "hybrid"
    top_k: int = 10


@dataclass
class LightRAGConfig:
    working_dir: str = "./lightrag_data"
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    entity_extract_max_gleaning: int = 1
    query: QueryConfig = field(default_factory=QueryConfig)


@dataclass
class PathsConfig:
    corpus_dir: str = "../simulation-theology-corpus/corpus"
    sdf_dir: str = "../simulation-theology-training-data/sdf"


@dataclass
class AppConfig:
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    lightrag: LightRAGConfig = field(default_factory=LightRAGConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def resolve_paths(self, base_dir: Path) -> None:
        """Resolve relative paths against the given base directory."""
        self.paths.corpus_dir = str((base_dir / self.paths.corpus_dir).resolve())
        self.paths.sdf_dir = str((base_dir / self.paths.sdf_dir).resolve())
        self.lightrag.working_dir = str(
            (base_dir / self.lightrag.working_dir).resolve()
        )


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file.

    If config_path is None, looks for config.yaml in the repo root
    (parent of the st_graphrag package directory).
    """
    if config_path is None:
        repo_root = Path(__file__).parent.parent
        config_path = repo_root / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        config = AppConfig()
        config.resolve_paths(config_path.parent)
        return config

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    claude_cfg = ClaudeConfig(**raw.get("claude", {}))
    embedding_cfg = EmbeddingConfig(**raw.get("embedding", {}))

    lightrag_raw = raw.get("lightrag", {})
    query_raw = lightrag_raw.pop("query", {})
    query_cfg = QueryConfig(**query_raw)
    lightrag_cfg = LightRAGConfig(**lightrag_raw, query=query_cfg)

    paths_cfg = PathsConfig(**raw.get("paths", {}))

    config = AppConfig(
        claude=claude_cfg,
        embedding=embedding_cfg,
        lightrag=lightrag_cfg,
        paths=paths_cfg,
    )
    config.resolve_paths(config_path.parent)
    return config
