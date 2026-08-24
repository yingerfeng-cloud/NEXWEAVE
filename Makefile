PYTHON ?= python3
PNPM ?= pnpm
DOCKER ?= docker

.PHONY: bootstrap format lint typecheck unit contract web-build check env dev-up dev-down dev-logs verify migration-check rustfs-spike

bootstrap:
	$(PYTHON) -m pip install -r requirements/dev.txt -c requirements/dev.lock
	$(PNPM) install --frozen-lockfile

format:
	$(PYTHON) -m ruff format --check .
	$(PNPM) format:check

lint:
	$(PYTHON) -m ruff check .
	$(PNPM) lint

typecheck:
	$(PYTHON) -m mypy
	$(PNPM) typecheck

unit:
	$(PYTHON) -m pytest -m "not integration"
	$(PNPM) test

contract:
	$(PYTHON) -m pytest packages/contracts/tests tests/contract

web-build:
	$(PNPM) build

check: format lint typecheck unit contract web-build

env:
	$(PYTHON) scripts/bootstrap_env.py

dev-up: env
	$(DOCKER) compose up --build --detach --wait

dev-down:
	$(DOCKER) compose down

dev-logs:
	$(DOCKER) compose logs --follow api worker-health web

verify:
	$(PYTHON) scripts/verify_m0.py

migration-check:
	$(DOCKER) compose exec -T api python scripts/check_migrations.py

rustfs-spike:
	$(PYTHON) scripts/verify_rustfs_spk004.py --output artifacts/spikes/spk004-local.json
