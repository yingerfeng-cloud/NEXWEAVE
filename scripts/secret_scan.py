"""Small deterministic secret-pattern gate for repository content."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{30,}"),
    "JWT": re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}


def candidate_files() -> list[Path]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required for the secret scan")
    result = subprocess.run(  # noqa: S603
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> None:
    findings: list[str] = []
    for path in candidate_files():
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    if findings:
        raise SystemExit("Potential secrets found:\n" + "\n".join(findings))
    print("Secret pattern scan passed")


if __name__ == "__main__":
    main()
