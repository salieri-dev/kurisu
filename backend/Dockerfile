
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev pkg-config libmagickwand-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /install

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgthread-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

WORKDIR /backend

COPY kurisu_core ./kurisu_core
RUN pip install --no-cache-dir ./kurisu_core

COPY backend/. .

RUN rm -rf ~/.cache/pip /wheels

RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /backend
USER backend

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "uvicorn_log_config.json", "--reload"]
