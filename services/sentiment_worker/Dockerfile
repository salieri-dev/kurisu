FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

# Declare build-args early so they don’t bust later cache
ARG SENTIMENT_MODEL
ARG SENSITIVE_TOPICS_MODEL

ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRANSFORMERS_CACHE=/opt/kurisu/cache \
    HF_HOME=/opt/kurisu/cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry"

WORKDIR /opt/kurisu/sentiment_worker

# Copy dependency files and local packages first to leverage Docker cache
COPY packages/kurisu_core ../kurisu_core/
COPY services/sentiment_worker/pyproject.toml services/sentiment_worker/poetry.lock ./

# Install Python dependencies
RUN poetry install --no-interaction --no-ansi --only main --no-root

# This RUN now uses the ARGs declared above to pre-download models
RUN python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
    sentiment_model = '${SENTIMENT_MODEL}'; \
    topics_model = '${SENSITIVE_TOPICS_MODEL}'; \
    print(f'Downloading sentiment model: {sentiment_model}'); \
    AutoTokenizer.from_pretrained(sentiment_model); \
    AutoModelForSequenceClassification.from_pretrained(sentiment_model); \
    print(f'Downloading topics model: {topics_model}'); \
    AutoTokenizer.from_pretrained(topics_model); \
    AutoModelForSequenceClassification.from_pretrained(topics_model);"

# Create a non-root user and copy the rest of the application code
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /opt/kurisu

COPY --chown=app:app services/sentiment_worker/. .

USER app

# Start the application
CMD ["python", "main.py"]