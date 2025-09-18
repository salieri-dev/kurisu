FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1
RUN pip install "poetry"

WORKDIR /opt/kurisu/dashboard

# Copy dependency files and local packages first to leverage Docker cache
COPY services/dashboard/pyproject.toml services/dashboard/poetry.lock ./
COPY packages/kurisu_core ../kurisu_core/

# Install Python dependencies into the system environment
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy the rest of the application code
COPY services/dashboard/. .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /opt/kurisu

USER appuser

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8001

# Start the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]