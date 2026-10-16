"""``[tool.docxtpl-lint]`` in pyproject.toml.

The nearest ``pyproject.toml`` (current directory upwards) that has a
``[tool.docxtpl-lint]`` table is used. Command line options override it.
Unknown keys are an error, so a typo never silently disables a check.

Example::

    [tool.docxtpl-lint]
    ignore = ["DTL002"]
    data = ["tests/sample_context.json"]   # relative to pyproject.toml
    warnings-as-errors = true
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

KEYS = {
    "select": (list, str),
    "ignore": (list, str),
    "data": (list, str),
    "allow-cross-paragraph": (bool,),
    "report-unused-data": (bool,),
    "warnings-as-errors": (bool,),
    "lang": (str,),
    "context": (int,),
    "baseline": (str,),
    "filters": (list, str),
    "tests": (list, str),
    "jinja-env": (str,),
}


class ConfigError(ValueError):
    pass


def find_config(start: Path | None = None) -> Path | None:
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        f = d / "pyproject.toml"
        if f.is_file():
            try:
                with f.open("rb") as fh:
                    if "docxtpl-lint" in tomllib.load(fh).get("tool", {}):
                        return f
            except (OSError, tomllib.TOMLDecodeError):
                continue
    return None


def load_config(path: Path) -> dict[str, Any]:
    """Return options with argparse-style names (``allow_cross_paragraph``)."""
    try:
        with path.open("rb") as fh:
            raw = tomllib.load(fh).get("tool", {}).get("docxtpl-lint", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in KEYS:
            raise ConfigError(f"{path}: unknown key [tool.docxtpl-lint] {key!r}; allowed: {', '.join(KEYS)}")
        if (isinstance(value, bool) and bool not in KEYS[key]) or not isinstance(value, KEYS[key]):
            raise ConfigError(f"{path}: [tool.docxtpl-lint] {key} has the wrong type")
        if key in ("select", "ignore", "filters", "tests") and isinstance(value, list):
            value = ",".join(value)
        if key == "data":
            items = [value] if isinstance(value, str) else value
            value = [str((path.parent / v).resolve()) for v in items]
        if key == "baseline":
            value = str((path.parent / value).resolve())
        if key == "lang" and value not in ("en", "zh"):
            raise ConfigError(f"{path}: [tool.docxtpl-lint] lang must be 'en' or 'zh'")
        out[key.replace("-", "_")] = value
    return out
