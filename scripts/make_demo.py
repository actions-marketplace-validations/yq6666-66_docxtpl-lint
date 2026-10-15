"""Regenerate docs/demo.svg and docs/demo-zh.svg (README screenshots).

pip install rich && python scripts/make_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from make_fixtures import build  # noqa: E402

from docxtpl_lint.cli import render_text  # noqa: E402
from docxtpl_lint.core import lint_path  # noqa: E402

FILES = ["issue378_unclosed.docx", "issue603_table_loop.docx", "issue644_percent.docx"]


def main() -> None:
    build(ROOT / "examples")
    os.chdir(ROOT)
    reports = [lint_path(f"examples/{f}") for f in FILES]
    for lang, name in (("en", "demo.svg"), ("zh", "demo-zh.svg")):
        out = render_text(reports, color=True, lang=lang)
        cmd = "$ docxtpl-lint examples/*.docx" + (" --lang zh" if lang == "zh" else "")
        console = Console(record=True, width=170, file=open(os.devnull, "w"))  # noqa: SIM115
        console.print(Text(cmd, style="bold green"))
        console.print(Text.from_ansi(out))
        console.save_svg(str(ROOT / "docs" / name), title="docxtpl-lint")
        print("wrote docs/" + name)


if __name__ == "__main__":
    main()
