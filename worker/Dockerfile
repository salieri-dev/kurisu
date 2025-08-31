FROM python:3.11-slim

# Install system dependencies (gcc is often needed for some Python packages).
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install latest Poetry and disable its virtualenv creation, for installing Python dependencies.
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/worker

# Copy dependency files and local packages first to leverage Docker cache
COPY worker/pyproject.toml worker/poetry.lock ./
COPY kurisu_core ../kurisu_core/

# Install Python dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# Copy the rest of the application code
COPY worker/. .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /opt/kurisu
USER app

# Standard python execution
CMD ["python", "main.py"]