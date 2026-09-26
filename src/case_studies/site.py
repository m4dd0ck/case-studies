"""Render every memo, plus an index, as a static site."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from case_studies.memos import airport, complaints

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


MEMOS = [
    Memo(
        "airport-queue",
        "Is the airport queue worth it?",
        "When should an NYC cab driver wait for an airport fare instead of heading back?",
        "NYC TLC yellow-cab trip records, 2025",
        airport.build,
    ),
    Memo(
        "card-complaints",
        "Which card complaints to fix first",
        "Which credit-card complaint issues are growing and costing issuers money?",
        "CFPB Consumer Complaint Database, 2024-2026",
        complaints.build,
    ),
]


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
        (out_dir / f"{memo.slug}.html").write_text(page, encoding="utf-8")
    index = out_dir / "index.html"
    index.write_text(_env.get_template("index.html.j2").render(memos=MEMOS), encoding="utf-8")
    (out_dir / SITE_MARKER).write_text("Built by memos site; safe to delete.\n", encoding="utf-8")
    return index
