PYTHON ?= python3
PNPM ?= pnpm
DOCKER ?= docker

.PHONY: bootstrap format lint typecheck unit contract sdk-check web-build check env dev-up dev-down dev-logs verify verify-m0 verify-m1 verify-m2 migration-check rustfs-spike

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

sdk-check:
	$(PNPM) --filter @nexweave/web exec prettier --check ../../packages/sdk/typescript
	$(PNPM) --filter @nexweave/web exec tsc -p ../../packages/sdk/typescript/tsconfig.json

web-build:
	$(PNPM) build

check: format lint typecheck unit contract sdk-check web-build

env:
	$(PYTHON) scripts/bootstrap_env.py

dev-up: env
	$(DOCKER) compose up --build --detach --wait

dev-down:
	$(DOCKER) compose down

dev-logs:
	$(DOCKER) compose logs --follow api worker-health worker-kernel web

verify:
	$(PYTHON) scripts/verify_m1.py
	$(PYTHON) scripts/verify_m2.py

verify-m0:
	$(PYTHON) scripts/verify_m0.py

verify-m1:
	$(PYTHON) scripts/verify_m1.py

verify-m2:
	$(PYTHON) scripts/verify_m2.py

migration-check:
	$(DOCKER) compose exec -T api python scripts/check_migrations.py

rustfs-spike:
	$(PYTHON) scripts/verify_rustfs_spk004.py --output artifacts/spikes/spk004-local.json
