"""Claude Code CLI wrapper as an async LLM function for LightRAG."""

import asyncio
import json
import logging
import time

from .config import ClaudeConfig

logger = logging.getLogger(__name__)

# Dedicated logger for full request/response capture
llm_io_logger = logging.getLogger("st_graphrag.llm_io")

# Module-level semaphore, initialized on first use
_semaphore: asyncio.Semaphore | None = None
_config: ClaudeConfig | None = None
_call_counter: int = 0


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
    It pipes the prompt via stdin to avoid shell parsing issues with special
    characters in LightRAG's extraction prompts.
    """
    global _semaphore, _config, _call_counter

    if _config is None:
        _config = ClaudeConfig()
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_config.max_concurrent)

    _call_counter += 1
    call_id = _call_counter

    # Build command — prompt is piped via stdin, not as an argument
    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--max-turns", str(_config.max_turns),
        "--model", _config.model,
    ]

    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    async with _semaphore:
        logger.info(
            "LLM call #%d: model=%s, prompt_len=%d chars",
            call_id, _config.model, len(prompt),
        )

        # Log the full prompt
        llm_io_logger.debug(
            "LLM CALL #%d REQUEST\n"
            "--- CMD ---\n%s\n"
            "--- SYSTEM PROMPT ---\n%s\n"
            "--- PROMPT (%d chars) ---\n%s\n"
            "--- END REQUEST #%d ---",
            call_id,
            " ".join(cmd),
            system_prompt or "(none)",
            len(prompt),
            prompt,
            call_id,
        )

        start_time = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=_config.timeout,
            )
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start_time
            logger.error(
                "LLM call #%d: TIMEOUT after %.1fs (limit=%ds)",
                call_id, elapsed, _config.timeout,
            )
            llm_io_logger.error(
                "LLM CALL #%d TIMEOUT after %.1fs", call_id, elapsed
            )
            raise
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. Ensure 'claude' is on your PATH "
                "and you have an active Max subscription."
            )

        elapsed = time.monotonic() - start_time

        if proc.returncode != 0:
            stderr_text = stderr.decode(errors="replace").strip()
            logger.error(
                "LLM call #%d: FAILED (exit code %d) after %.1fs: %s",
                call_id, proc.returncode, elapsed, stderr_text[:200],
            )
            llm_io_logger.error(
                "LLM CALL #%d FAILED (exit code %d, %.1fs)\n"
                "--- STDERR ---\n%s\n"
                "--- END ERROR #%d ---",
                call_id, proc.returncode, elapsed, stderr_text, call_id,
            )
            raise RuntimeError(
                f"Claude CLI failed (exit code {proc.returncode}): {stderr_text}"
            )

        stdout_text = stdout.decode(errors="replace").strip()

        try:
            result_json = json.loads(stdout_text)
            result_text = result_json["result"]
            tokens = result_json.get("cost", {})
            input_tokens = tokens.get("input_tokens", 0)
            output_tokens = tokens.get("output_tokens", 0)

            logger.info(
                "LLM call #%d: OK (%.1fs, %d input tokens, %d output tokens, %d chars response)",
                call_id, elapsed, input_tokens, output_tokens, len(result_text),
            )

            # Log the full response
            llm_io_logger.debug(
                "LLM CALL #%d RESPONSE (%.1fs)\n"
                "--- TOKENS ---\n"
                "input_tokens: %d\n"
                "output_tokens: %d\n"
                "cache_creation: %d\n"
                "cache_read: %d\n"
                "--- RESULT (%d chars) ---\n%s\n"
                "--- END RESPONSE #%d ---",
                call_id, elapsed,
                input_tokens, output_tokens,
                tokens.get("cache_creation_input_tokens", 0),
                tokens.get("cache_read_input_tokens", 0),
                len(result_text), result_text,
                call_id,
            )

            return result_text

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                "LLM call #%d: JSON parse error after %.1fs: %s",
                call_id, elapsed, e,
            )
            llm_io_logger.error(
                "LLM CALL #%d JSON PARSE ERROR\n"
                "--- RAW STDOUT (%d chars) ---\n%s\n"
                "--- END ERROR #%d ---",
                call_id, len(stdout_text), stdout_text[:5000], call_id,
            )
            return stdout_text
