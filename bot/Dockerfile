FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# --- START: Optimized Layering ---

# 1. Copy and install third-party dependencies first.
# This layer is only invalidated if requirements.txt changes.
COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy and install the local shared library next.
# This layer is only invalidated if the kurisu_core source code changes.
COPY kurisu_core ./kurisu_core
RUN pip install --no-cache-dir ./kurisu_core

# 3. Finally, copy the application code, which changes most frequently.
# Changing a file in `bot/` will now only invalidate this layer and subsequent ones.
COPY bot/. .

# --- END: Optimized Layering ---

RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /app
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "main.py"]
