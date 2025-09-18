FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

ARG SENTIMENT_MODEL
ARG SENSITIVE_TOPICS_MODEL

# 1. Install Poetry and system dependencies
ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRANSFORMERS_CACHE=/app/cache \
    HF_HOME=/app/cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry"

# 2. Set up the application directory structure
WORKDIR /app

# 3. Copy dependency definitions AND the full local package source
COPY services/sentiment_worker/pyproject.toml services/sentiment_worker/poetry.lock ./services/sentiment_worker/
COPY packages/kurisu_core ./packages/kurisu_core

# 4. Install Python dependencies
WORKDIR /app/services/sentiment_worker
RUN poetry install --no-interaction --no-ansi --only main --no-root

# # 5. Pre-download models to a cache layer
# RUN python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
#     sentiment_model = '${SENTIMENT_MODEL}'; \
#     topics_model = '${SENSITIVE_TOPICS_MODEL}'; \
#     print(f'Downloading sentiment model: {sentiment_model}'); \
#     AutoTokenizer.from_pretrained(sentiment_model); \
#     AutoModelForSequenceClassification.from_pretrained(sentiment_model); \
#     print(f'Downloading topics model: {topics_model}'); \
#     AutoTokenizer.from_pretrained(topics_model); \
#     AutoModelForSequenceClassification.from_pretrained(topics_model);"

# 6. Copy the service's source code
WORKDIR /app
COPY services/sentiment_worker/. ./services/sentiment_worker/

# 7. Create and switch to a non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 8. Set final workdir and run the application
WORKDIR /app/services/sentiment_worker
CMD ["python", "main.py"]