"""Fetch fixed public safetensors, verifying both weight and config SHA-256."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
FILES = {
    "config.json": ("ef1143bfdc9c0376d9a056eefca46cb4b1ec3d0ffacd541ff56feb40fb708031", 16_384),
    "model.safetensors": (
        "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42",
        600_000_000,
    ),
}


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Use hf-mirror.com transport, still verify pinned hashes",
    )
    args = parser.parse_args()
    host = "hf-mirror.com" if args.mirror else "huggingface.co"
    root = ROOT / ".nexweave-data/models/chronos-2"
    root.mkdir(parents=True, exist_ok=True)
    for name, (digest, budget) in FILES.items():
        target = root / name
        if target.is_file() and checksum(target) == digest:
            continue
        temporary = target.with_suffix(target.suffix + ".part")
        url = f"https://{host}/amazon/chronos-2/resolve/{REVISION}/{name}"
        with urlopen(url, timeout=60) as response, temporary.open("wb") as output:  # noqa: S310 - fixed HTTPS hosts
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > budget:
                    raise ValueError("Model download exceeds size limit")
                output.write(block)
        if checksum(temporary) != digest:
            raise ValueError("Model hash mismatch; file was not installed")
        temporary.replace(target)
    (root / "provenance.json").write_text(
        json.dumps(
            {
                "model": "amazon/chronos-2",
                "revision": REVISION,
                "hashes": {k: v[0] for k, v in FILES.items()},
                "transport_host": host,
            },
            indent=2,
        )
    )
    print("Pinned model and config verified; no remote Python code is loaded.")


if __name__ == "__main__":
    main()
