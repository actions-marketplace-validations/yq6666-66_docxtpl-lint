"""docxtpl-lint: static linter for docxtpl (python-docx-template) Word templates.

Public, semver-stable API: see :mod:`docxtpl_lint.api` and docs/api.md.
"""

from typing import Any

from .api import Result, Template, TemplateLintError, check_context, effective_autoescape, infer_schema, lint
from .core import Issue, Location

__all__ = [
    "Issue",
    "Location",
    "Result",
    "Template",
    "TemplateLintError",
    "check_context",
    "effective_autoescape",
    "infer_schema",
    "lint",
]
__version__ = "2.0.1"


def __getattr__(name: str) -> Any:
    if name == "lint_path":  # deprecated in 2.0, removed in 3.0 (docs/MIGRATION-2.0.md)
        import warnings

        from .core import lint_path

        warnings.warn(
            "docxtpl_lint.lint_path is deprecated and will be removed in 3.0; use docxtpl_lint.lint "
            "(returns a Result; takes paths, bytes or file objects)",
            DeprecationWarning,
            stacklevel=2,
        )
        return lint_path
    raise AttributeError(f"module 'docxtpl_lint' has no attribute {name!r}")
