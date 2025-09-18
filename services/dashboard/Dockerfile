FROM python:3.11-slim

# 1. Install Poetry
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1
RUN pip install "poetry"

# 2. Set up the application directory structure
WORKDIR /app

# 3. Copy dependency definitions AND the full local package source
COPY services/dashboard/pyproject.toml services/dashboard/poetry.lock ./services/dashboard/
COPY packages/kurisu_core ./packages/kurisu_core

# 4. Install dependencies
WORKDIR /app/services/dashboard
RUN poetry install --no-interaction --no-ansi --only main --no-root

# 5. Copy the service's source code
WORKDIR /app
COPY services/dashboard/. ./services/dashboard/

# 6. Create and switch to a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 7. Set final workdir and run the application
WORKDIR /app/services/dashboard
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]