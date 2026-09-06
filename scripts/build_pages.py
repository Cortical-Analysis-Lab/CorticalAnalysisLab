"""Assemble the public site from main and the fellowship database branch."""

import argparse
from pathlib import Path
import shutil


def build(main: Path, fellowship: Path, output: Path) -> None:
    # Require a fresh directory so obsolete files cannot leak into a deployment.
    output.mkdir(parents=True, exist_ok=False)
    for source in main.glob("*.html"):
        shutil.copy2(source, output / source.name)
    for directory in ("assets", "data", "partials"):
        shutil.copytree(main / directory, output / directory)
    shutil.copy2(main / "CNAME", output / "CNAME")

    for relative in (
        "fellowship-database.html",
        "assets/fellowship-database.css",
        "assets/fellowship-results.css",
        "assets/fellowship-questionnaire.js",
        "database/research_opportunities.sqlite",
    ):
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fellowship / relative, destination)
    shutil.copytree(
        fellowship / "data/summer-research",
        output / "data/summer-research",
        dirs_exist_ok=True,
    )
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", required=True, type=Path)
    parser.add_argument("--fellowship", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.main, args.fellowship, args.output)
