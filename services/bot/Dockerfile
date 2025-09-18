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
COPY services/bot/pyproject.toml services/bot/poetry.lock ./services/bot/
COPY packages/kurisu_core ./packages/kurisu_core

# 5. Install dependencies
WORKDIR /app/services/bot
RUN poetry install --no-interaction --no-ansi --only main --no-root

# 6. Copy the service's source code
WORKDIR /app
COPY services/bot/. ./services/bot/

# 7. Create and switch to a non-root user
RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /app
USER botuser

# 8. Set final workdir and run the application
WORKDIR /app/services/bot
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "main.py"]