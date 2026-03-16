"""Tests for llm_provider module.

Note: These tests verify the module structure, not actual Claude CLI calls.
Integration tests that call claude -p require an active Max subscription.
"""

import pytest

from st_graphrag.config import ClaudeConfig
from st_graphrag.llm_provider import configure


class TestLLMProviderConfig:
    def test_configure_sets_defaults(self):
        config = ClaudeConfig()
        configure(config)

        assert config.model == "opus"
        assert config.max_turns == 1
        assert config.timeout == 120
        assert config.max_concurrent == 2

    def test_configure_custom_model(self):
        config = ClaudeConfig(model="sonnet", max_concurrent=4)
        configure(config)

        assert config.model == "sonnet"
        assert config.max_concurrent == 4
