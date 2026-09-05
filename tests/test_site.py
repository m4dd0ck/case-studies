from pathlib import Path

import pytest

from case_studies.site import MEMOS, SITE_MARKER, UnsafeOutputError, build_site


def test_site_has_index_and_every_memo(tmp_path: Path) -> None:
    out = tmp_path / "site"
    build_site(out)
    for memo in MEMOS:
        page = (out / f"{memo.slug}.html").read_text()
        assert memo.title in page or memo.title.replace("'", "&#39;") in page
    assert (out / SITE_MARKER).exists()


def test_site_refuses_to_replace_a_folder_it_did_not_build(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("keep me")
    with pytest.raises(UnsafeOutputError):
        build_site(tmp_path)
    assert (tmp_path / "notes.txt").exists()


def test_site_rebuilds_over_its_own_output(tmp_path: Path) -> None:
    out = tmp_path / "site"
    build_site(out)
    build_site(out)
    assert (out / "index.html").exists()
