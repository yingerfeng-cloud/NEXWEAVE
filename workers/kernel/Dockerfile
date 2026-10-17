FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime

COPY infra/security/debian12-packages.txt /tmp/nxw-security-packages.txt
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update -o Acquire::Retries=2 \
    && xargs -r -a /tmp/nxw-security-packages.txt apt-get install --yes --no-install-recommends --only-upgrade \
    && rm -rf /var/lib/apt/lists/* /tmp/nxw-security-packages.txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api/src:/app/packages/domain/src:/app/packages/application/src:/app/packages/contracts/src:/app/workers/kernel/src

WORKDIR /app

RUN groupadd --system --gid 10001 nexweave \
    && useradd --system --uid 10001 --gid nexweave --home-dir /app nexweave

COPY requirements/runtime.txt requirements/runtime.lock requirements/
RUN pip install --no-cache-dir --requirement requirements/runtime.txt --constraint requirements/runtime.lock

COPY apps/api/src apps/api/src
COPY packages/domain packages/domain
COPY packages/application packages/application
COPY packages/contracts packages/contracts
COPY workers/kernel workers/kernel

USER nexweave

CMD ["python", "-m", "nexweave_worker_kernel.main"]
