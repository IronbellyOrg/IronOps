"""``claude plugin validate`` subprocess wrapper.

Implements FR-5 (validation gate), FR-9 (atomicity gate — validate
before publish), NFR-4 (zero errors, zero warnings — strict-warnings),
and NFR-7 part (c) (full log retained).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ironops.errors import ValidateFailed

VALIDATOR_TIMEOUT_SECONDS: int = 60

_WARNING_RES = [
    re.compile(r"\bwarning\b", re.IGNORECASE),
    re.compile(r"\bWARN\b"),
]


@dataclass(frozen=True)
class ValidatorResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float


def _resolve_claude_binary() -> str:
    """Resolve the claude CLI binary path.

    Prefers ``CLAUDE_BIN`` env override, falls back to ``shutil.which``.
    """
    env = os.environ.get("CLAUDE_BIN")
    if env:
        return env
    found = shutil.which("claude")
    if not found:
        raise RuntimeError(
            "claude CLI not found in PATH; set CLAUDE_BIN env var or install Claude Code"
        )
    return found


def run_validator(staging_dir: Path, log_dir: Path | None = None) -> ValidatorResult:
    """Invoke ``claude plugin validate <staging_dir>``.

    Returns a ValidatorResult capturing exit_code, stdout, stderr, and
    duration. When ``log_dir`` is provided the full output is persisted to
    ``<log_dir>/validate.log`` regardless of exit code (NFR-7 part c).
    Raises ValidateFailed when exit_code != 0 OR stdout/stderr contains
    warning patterns (NFR-4 strict-warnings).
    """
    claude_bin = _resolve_claude_binary()
    start = time.monotonic()
    proc = subprocess.run(
        [claude_bin, "plugin", "validate", str(staging_dir)],
        capture_output=True,
        text=True,
        timeout=VALIDATOR_TIMEOUT_SECONDS,
        check=False,
    )
    duration_s = time.monotonic() - start
    result = ValidatorResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_s=duration_s,
    )

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "validate.log"
        log_file.write_text(
            f"# claude plugin validate {staging_dir}\n"
            f"# exit_code={result.exit_code} duration_s={duration_s:.3f}\n"
            f"# --- stdout ---\n{result.stdout}\n"
            f"# --- stderr ---\n{result.stderr}\n"
        )

    if result.exit_code != 0:
        raise ValidateFailed(
            f"claude plugin validate exited {result.exit_code}: "
            f"{(result.stderr or result.stdout).strip().splitlines()[0] if (result.stderr or result.stdout).strip() else 'no output'}"
        )

    combined = result.stdout + "\n" + result.stderr
    for wre in _WARNING_RES:
        if wre.search(combined):
            raise ValidateFailed(
                f"claude plugin validate emitted warnings (NFR-4 strict-warnings): "
                f"{combined.strip().splitlines()[0]}"
            )

    return result
