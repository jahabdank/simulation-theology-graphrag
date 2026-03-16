"""Claude Code CLI wrapper as an async LLM function for LightRAG."""

import asyncio
import json
import logging

from .config import ClaudeConfig

logger = logging.getLogger(__name__)

# Module-level semaphore, initialized on first use
_semaphore: asyncio.Semaphore | None = None
_config: ClaudeConfig | None = None


def configure(config: ClaudeConfig) -> None:
    """Configure the LLM provider with Claude settings."""
    global _semaphore, _config
    _config = config
    _semaphore = asyncio.Semaphore(config.max_concurrent)


async def claude_code_llm(
    prompt: str,
    system_prompt: str | None = None,
    **kwargs,
) -> str:
    """Async LLM function that calls Claude Code CLI.

    This function matches the signature LightRAG expects for llm_model_func.
    It calls `claude -p` with --output-format json and returns the text result.
    """
    global _semaphore, _config

    if _config is None:
        _config = ClaudeConfig()
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_config.max_concurrent)

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--max-turns",
        str(_config.max_turns),
        "--model",
        _config.model,
    ]

    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    async with _semaphore:
        logger.debug(
            "Calling claude -p (model=%s, prompt_len=%d)",
            _config.model,
            len(prompt),
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=_config.timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Claude CLI timed out after %ds", _config.timeout)
            raise
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. Ensure 'claude' is on your PATH "
                "and you have an active Max subscription."
            )

        if proc.returncode != 0:
            stderr_text = stderr.decode(errors="replace").strip()
            logger.error(
                "Claude CLI exited with code %d: %s", proc.returncode, stderr_text
            )
            raise RuntimeError(
                f"Claude CLI failed (exit code {proc.returncode}): {stderr_text}"
            )

        stdout_text = stdout.decode(errors="replace").strip()
        try:
            result = json.loads(stdout_text)
            return result["result"]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse Claude CLI output: %s", e)
            # Fall back to raw output if JSON parsing fails
            return stdout_text
