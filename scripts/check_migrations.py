"""Exercise the full M0 migration rollback path in a disposable local database."""

from __future__ import annotations

import subprocess
import sys


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, "-m", "alembic", *arguments], check=True)  # noqa: S603


def main() -> None:
    run("downgrade", "base")
    run("upgrade", "head")
    run("downgrade", "base")
    run("upgrade", "head")
    print("M0 migration upgrade/downgrade/re-upgrade passed")


if __name__ == "__main__":
    main()
