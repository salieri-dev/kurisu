FROM python:3.11-slim

# 1. Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# 2. Install Poetry
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1
RUN pip install "poetry"

# 3. Set up the application directory structure
WORKDIR /app

# 4. Copy dependency definitions AND the full local package source
COPY services/worker/pyproject.toml services/worker/poetry.lock ./services/worker/
COPY packages/kurisu_core ./packages/kurisu_core

# 5. Install dependencies
WORKDIR /app/services/worker
RUN poetry install --no-interaction --no-ansi --only main --no-root

# 6. Copy the service's source code
WORKDIR /app
COPY services/worker/. ./services/worker/

# 7. Create and switch to a non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 8. Set final workdir and run the application
WORKDIR /app/services/worker
CMD ["python", "main.py"]