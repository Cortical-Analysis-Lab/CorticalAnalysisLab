"""Assemble the lab website from main; fellowship publication is suspended."""

import argparse
from pathlib import Path
import shutil


def build(main: Path, output: Path) -> None:
    # Require a fresh directory so obsolete files cannot leak into a deployment.
    output.mkdir(parents=True, exist_ok=False)
    for source in main.glob("*.html"):
        shutil.copy2(source, output / source.name)
    for directory in ("assets", "data", "partials"):
        shutil.copytree(main / directory, output / directory)
    shutil.copy2(main / "CNAME", output / "CNAME")

    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.main, args.output)
