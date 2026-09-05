"""``memos`` command line interface."""

from pathlib import Path
from typing import Annotated

import typer

from case_studies import cfpb, taxi
from case_studies.site import build_site

app = typer.Typer(help="Short analytical memos on public data.", no_args_is_help=True)


@app.command("extract-taxi")
def extract_taxi(year: Annotated[int, typer.Option()] = 2025) -> None:
    """Rebuild the taxi snapshot from TLC trip records (downloads ~700 MB)."""
    typer.echo(f"Snapshot: {taxi.extract(year)}")


@app.command("extract-cfpb")
def extract_cfpb() -> None:
    """Rebuild the complaint snapshots from the CFPB API."""
    typer.echo(f"Snapshots: {cfpb.extract()}")


@app.command()
def site(out: Annotated[Path, typer.Option()] = Path("site")) -> None:
    """Render the memos from the committed snapshots (no network)."""
    typer.echo(f"Site: {build_site(out)}")
