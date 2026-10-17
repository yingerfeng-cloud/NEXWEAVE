"""Credential-free offline numerical worker, terminated on Activity cancellation."""

import contextlib
import json
import sys

from nexweave_api.forecast_gateway import Chronos2Provider
from nexweave_api.settings import Settings


def main() -> None:
    payload = json.loads(sys.stdin.buffer.read(8_000_001))
    Settings.model_config = {**Settings.model_config, "env_file": None}
    settings = Settings(
        forecast_model_path=payload["model_path"],
        forecast_model_revision=payload["model_revision"],
    )
    with contextlib.redirect_stdout(sys.stderr):
        result = Chronos2Provider(settings)._forecast(
            payload["context"],
            on_ready=lambda: print('{"event":"MODEL_READY"}', file=sys.__stdout__, flush=True),
        )
    sys.stdout.write(json.dumps(result, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
