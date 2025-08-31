# ---- Build Stage ----
FROM python:3.11-slim as builder

# ... (build stage remains the same)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev pkg-config libmagickwand-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# ---- Final Stage ----
FROM python:3.11-slim

# ... (runtime dependencies installation remains the same)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgthread-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

WORKDIR /backend
COPY kurisu_core ./kurisu_core
COPY backend/. .

RUN pip install --no-cache-dir ./kurisu_core && \
    rm -rf ~/.cache/pip /wheels

RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /backend
USER backend

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

# NEW: Use a production-ready command with the silent log config.
# Our Python code will override this with the correct structlog config once it runs.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "uvicorn_log_config.json", "--reload"]
