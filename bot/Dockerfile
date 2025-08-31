# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

WORKDIR /opt/kurisu

COPY bot/pyproject.toml bot/poetry.lock ./bot/
COPY kurisu_core ./kurisu_core/

WORKDIR /opt/kurisu/bot

RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --without dev --no-root


# ---- Final Stage ----
FROM python:3.11-slim

WORKDIR /opt/kurisu/bot

COPY --from=builder /opt/kurisu/bot/.venv ./.venv
ENV PATH="/opt/kurisu/bot/.venv/bin:$PATH"

COPY bot/. .
COPY kurisu_core ../kurisu_core/

RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /opt/kurisu
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "main.py"]