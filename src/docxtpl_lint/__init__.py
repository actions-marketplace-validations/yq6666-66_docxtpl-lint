"""docxtpl-lint: static linter for docxtpl (python-docx-template) Word templates."""

from .api import Result, TemplateLintError, check_context, infer_schema, lint
from .core import Issue, Location, lint_path

__all__ = ["Issue", "Location", "Result", "TemplateLintError", "check_context", "infer_schema", "lint", "lint_path"]
__version__ = "1.9.0"
