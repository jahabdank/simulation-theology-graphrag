"""Tests for the query module structure.

Note: Integration tests that actually query LightRAG require a seeded graph.
These tests verify the module can be imported and configured.
"""

from st_graphrag.config import load_config


class TestQueryConfig:
    def test_config_loads(self):
        config = load_config()
        assert config.lightrag.query.default_mode == "hybrid"
        assert config.lightrag.query.top_k == 10

    def test_paths_resolve(self):
        config = load_config()
        assert "simulation-theology-corpus" in config.paths.corpus_dir
        assert "simulation-theology-training-data" in config.paths.sdf_dir
