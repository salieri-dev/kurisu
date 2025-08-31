# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# --- Simplified: Install latest Poetry and disable its virtualenv creation ---
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/bot

COPY bot/pyproject.toml bot/poetry.lock ./
COPY kurisu_core ../kurisu_core/

# Install dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# ---- Final Stage ----
FROM python:3.11-slim

WORKDIR /opt/kurisu/bot

# Copy globally installed packages and their executables
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY bot/. .
COPY kurisu_core ../kurisu_core/

RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /opt/kurisu
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Standard python execution
CMD ["python", "main.py"]