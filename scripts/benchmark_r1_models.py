"""Required real-provider synthetic baseline; missing models block without invented scores."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from verify_m5 import _login

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    args = parser.parse_args()
    if urlsplit(args.base_url).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("The scripted technical-role benchmark is loopback-only")
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def blocked(reason: str) -> None:
        result = {
            "status": "CONFIGURATION_BLOCKED",
            "reason": reason,
            "model_calls": 0,
            "scored_evaluation": False,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        raise SystemExit(2)

    raw = args.config.read_text() if args.config else values.get("NEXWEAVE_BENCHMARK_MODEL_CONFIG")
    if (
        not raw
        or not values.get("NEXWEAVE_MODEL_GATEWAY_API_KEY")
        or not str(values.get("NEXWEAVE_MODEL_GATEWAY_ENDPOINT", "")).startswith("https://")
    ):
        blocked(
            "Configure HTTPS Model Gateway, its key, and public text/embedding model revisions."
        )
    try:
        config = json.loads(str(raw))
        assert isinstance(config, dict) and set(config) == {"text", "embedding"}
        for kind in ("text", "embedding"):
            item = config[kind]
            if kind == "text" and set(item) - {"model_name", "revision", "response_model"}:
                raise ValueError("unsupported text model metadata")
            assert isinstance(item, dict) and not set(item) - {
                "model_name",
                "revision",
                "response_model",
                "dimensions",
                "send_dimensions",
            }
            assert all(
                isinstance(item.get(k), str) and item[k].strip() for k in ("model_name", "revision")
            )
        dims = config["embedding"]["dimensions"]
        assert isinstance(dims, int) and not isinstance(dims, bool) and 1 <= dims <= 4096
    except (ValueError, TypeError, KeyError, AssertionError):
        blocked("Public model configuration is incomplete or unsupported; no calls were sent.")
    if args.check_config:
        result = {
            "status": "CONFIGURATION_READY_NOT_EVALUATED",
            "model_calls": 0,
            "scored_evaluation": False,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return
    profiles = {}
    with httpx.Client(base_url=args.base_url, timeout=120, trust_env=False) as client:
        admin = _login(client, "local-admin")
        for kind, capability in (("text", "structured_output"), ("embedding", "embedding")):
            item = config[kind]
            provider_config = {"revision": item["revision"], "capability": capability}
            for key in ("response_model", "dimensions", "send_dimensions"):
                if item.get(key) is not None and item.get(key) != "":
                    provider_config[key] = item[key]
            profile = admin.request(
                "POST",
                "/model-profiles",
                idempotency_key=str(uuid4()),
                json={
                    "space_id": None,
                    "name": "Real-provider synthetic baseline " + kind,
                    "provider": "openai-compatible",
                    "model_name": item["model_name"],
                    "credential_ref": "env://NEXWEAVE_MODEL_GATEWAY_API_KEY",
                    "externally_hosted": True,
                    "maximum_classification": "INTERNAL",
                    "config": provider_config,
                },
            ).json()
            profiles[kind] = profile["id"]
    result = subprocess.run(  # noqa: S603 - fixed runner, public profile identifiers, no credentials in argv
        [
            sys.executable,
            str(ROOT / "scripts/benchmark_r1_knowledge.py"),
            "--base-url",
            args.base_url,
            "--strategy",
            "SEMANTIC",
            "--text-model-profile-id",
            profiles["text"],
            "--embedding-model-profile-id",
            profiles["embedding"],
            "--output",
            str(args.output),
        ],
        cwd=ROOT,
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
