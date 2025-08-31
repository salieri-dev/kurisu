# Use a base image that is compatible with wkhtmltopdf's dependencies.
# python:3.11-slim-bullseye is based on Debian 11 "Bullseye".
FROM python:3.11-slim-bullseye

# Install all system dependencies (build-time and runtime).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    wkhtmltopdf \
    libmagic1 \
    libmagickwand-dev \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install latest Poetry and disable its virtualenv creation, for installing Python dependencies.
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/backend

# Copy dependency files and local packages first to leverage Docker cache
COPY backend/pyproject.toml backend/poetry.lock ./
COPY kurisu_core ../kurisu_core/

# Install Python dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# Copy the rest of the application code
COPY backend/. .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /opt/kurisu
USER backend

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

# Use python -m for robust execution
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "uvicorn_log_config.json"]