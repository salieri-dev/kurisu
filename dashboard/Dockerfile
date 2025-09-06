# Path: dashboard/Dockerfile
FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /opt/kurisu/dashboard

COPY dashboard/pyproject.toml dashboard/poetry.lock ./
COPY kurisu_core ../kurisu_core/

RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY dashboard/. .

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /opt/kurisu
USER appuser

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8001

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]