FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api/src:/app/packages/domain/src:/app/packages/contracts/src:/app/workers/health/src

WORKDIR /app

RUN groupadd --system --gid 10001 nexweave \
    && useradd --system --uid 10001 --gid nexweave --home-dir /app nexweave

COPY requirements/runtime.txt requirements/runtime.lock requirements/
RUN pip install --no-cache-dir --requirement requirements/runtime.txt --constraint requirements/runtime.lock

COPY apps/api/src apps/api/src
COPY packages/domain packages/domain
COPY packages/contracts packages/contracts
COPY workers/health workers/health

USER nexweave

CMD ["python", "-m", "nexweave_worker_health.main"]
