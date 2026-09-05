"""Render every memo, plus an index, as a static site."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

SITE_MARKER = ".memos-site"
_env = Environment(
    loader=PackageLoader("case_studies", "templates"), autoescape=select_autoescape(["j2"])
)


@dataclass(frozen=True)
class Memo:
    slug: str
    title: str
    question: str
    data: str
    build: Callable[[], dict[str, Any]]


MEMOS: list[Memo] = []


class UnsafeOutputError(ValueError):
    """Raised instead of deleting a folder this tool did not create."""


def build_site(out_dir: Path) -> Path:
    if out_dir.exists():
        if any(out_dir.iterdir()) and not (out_dir / SITE_MARKER).exists():
            raise UnsafeOutputError(f"{out_dir} is not empty and was not built by memos site")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for memo in MEMOS:
        page = _env.get_template(f"{memo.slug}.html.j2").render(memo=memo, **memo.build())
        (out_dir / f"{memo.slug}.html").write_text(page)
    index = out_dir / "index.html"
    index.write_text(_env.get_template("index.html.j2").render(memos=MEMOS))
    (out_dir / SITE_MARKER).write_text("Built by memos site; safe to delete.\n")
    return index
