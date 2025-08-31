# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libmagic1 imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgthread-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Simplified: Install latest Poetry and disable its virtualenv creation ---
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/backend

COPY backend/pyproject.toml backend/poetry.lock ./
COPY kurisu_core ../kurisu_core/

# Install dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# ---- Final Stage ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libmagic1 imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgthread-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kurisu/backend

# Copy globally installed packages and their executables
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/. .
COPY kurisu_core ../kurisu_core/

RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /opt/kurisu
USER backend

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

# Use python -m for robust execution
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "uvicorn_log_config.json"]