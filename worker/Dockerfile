# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

WORKDIR /opt/kurisu

COPY worker/pyproject.toml worker/poetry.lock ./worker/
COPY kurisu_core ./kurisu_core/

WORKDIR /opt/kurisu/worker

RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --without dev --no-root


# ---- Final Stage ----
FROM python:3.11-slim

WORKDIR /opt/kurisu/worker

COPY --from=builder /opt/kurisu/worker/.venv ./.venv
ENV PATH="/opt/kurisu/worker/.venv/bin:$PATH"

COPY worker/. .
COPY kurisu_core ../kurisu_core/

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /opt/kurisu
USER app

CMD ["python", "main.py"]