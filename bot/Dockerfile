FROM python:3.11-slim

# Install system dependencies (gcc is often needed for some Python packages).
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install latest Poetry and disable its virtualenv creation, for installing Python dependencies.
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/bot

# Copy dependency files and local packages first to leverage Docker cache
COPY bot/pyproject.toml bot/poetry.lock ./
COPY kurisu_core ../kurisu_core/

# Install Python dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# Copy the rest of the application code
COPY bot/. .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /opt/kurisu
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Standard python execution
CMD ["python", "main.py"]