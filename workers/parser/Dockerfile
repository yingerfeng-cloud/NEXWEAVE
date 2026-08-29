FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/workers/parser/src:/workspace/apps/api/src:/workspace/packages/domain/src:/workspace/packages/application/src:/workspace/packages/contracts/src

WORKDIR /workspace
COPY requirements/runtime.lock /workspace/requirements/runtime.lock
RUN pip install --no-cache-dir -r /workspace/requirements/runtime.lock
COPY packages /workspace/packages
COPY apps/api /workspace/apps/api
COPY workers/parser /workspace/workers/parser
RUN addgroup --system --gid 10001 nexweave \
    && adduser --system --uid 10001 --ingroup nexweave --home /nonexistent --no-create-home nexweave
USER 10001:10001

CMD ["python", "-m", "nexweave_worker_parser.main"]
