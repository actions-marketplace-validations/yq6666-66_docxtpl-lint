"""docxtpl-lint: static linter for docxtpl (python-docx-template) Word templates."""

from .core import Issue, Location, lint_path

__all__ = ["Issue", "Location", "lint_path"]
__version__ = "1.8.0"
