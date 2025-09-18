FROM python:3.11-slim-bullseye

# 1. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    wkhtmltopdf \
    libmagic1 \
    libmagickwand-dev \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Poetry
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1
RUN pip install "poetry"

# 3. Set up the application directory structure
WORKDIR /app

# 4. Copy dependency definitions AND the full local package source
COPY services/backend/pyproject.toml services/backend/poetry.lock ./services/backend/
COPY packages/kurisu_core ./packages/kurisu_core

# 5. Install dependencies
WORKDIR /app/services/backend
RUN poetry install --no-interaction --no-ansi --only main --no-root

# 6. Copy the service's source code
WORKDIR /app
COPY services/backend/. ./services/backend/

# 7. Create and switch to a non-root user
RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /app
USER backend

# 8. Set final workdir and run the application
WORKDIR /app/services/backend
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "uvicorn_log_config.json"]