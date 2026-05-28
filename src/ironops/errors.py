"""Exit codes and BuilderError hierarchy.

Implements NFR-7 (Failure transparency) — every build failure raises a
BuilderError subclass that carries one of the 9 categorical ExitCode
values (per amended spec §NFR-7, disposition D3 adding PUBLISH_FAILED).
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Categorical exit codes per amended spec §NFR-7 (9 user-visible codes + SUCCESS + INTERNAL_ERROR)."""

    SUCCESS = 0
    MANIFEST_INVALID = 10
    UNRESOLVED_IMPORT = 11
    CO_IMPORT_MISSING = 12
    VALIDATE_FAILED = 13
    PATH_ESCAPE = 14
    UPSTREAM_CLONE_FAILED = 15
    SELF_OVERWRITE = 16
    BUILDER_DIRTY_TREE = 17
    PUBLISH_FAILED = 18  # D3 — added per amended NFR-7
    INTERNAL_ERROR = 99


class BuilderError(Exception):
    """Base class for all categorical build failures.

    Subclasses set the `code` class attribute to the matching ExitCode.
    Each instance carries a `summary` string used for the NFR-7 one-line
    stderr message.
    """

    code: ExitCode = ExitCode.INTERNAL_ERROR

    def __init__(self, summary: str) -> None:
        super().__init__(summary)
        self.summary: str = summary


class ManifestInvalid(BuilderError):
    code = ExitCode.MANIFEST_INVALID


class UnresolvedImport(BuilderError):
    code = ExitCode.UNRESOLVED_IMPORT


class CoImportMissing(BuilderError):
    code = ExitCode.CO_IMPORT_MISSING


class ValidateFailed(BuilderError):
    code = ExitCode.VALIDATE_FAILED


class PathEscape(BuilderError):
    code = ExitCode.PATH_ESCAPE


class UpstreamCloneFailed(BuilderError):
    code = ExitCode.UPSTREAM_CLONE_FAILED


class SelfOverwrite(BuilderError):
    code = ExitCode.SELF_OVERWRITE


class BuilderDirtyTree(BuilderError):
    code = ExitCode.BUILDER_DIRTY_TREE


class PublishFailed(BuilderError):
    code = ExitCode.PUBLISH_FAILED


def format_failure(err: BuilderError) -> str:
    """Render a NFR-7 part (a) one-line stderr summary.

    Output shape: ``[<CODE_NAME>] <summary>`` with no embedded newlines.
    """
    summary = err.summary.replace("\n", " ").replace("\r", " ")
    return f"[{err.code.name}] {summary}"
