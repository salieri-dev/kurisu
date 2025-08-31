# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev pkg-config libmagickwand-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

# Create a root directory for the whole project
WORKDIR /opt/kurisu

# Copy dependency files into their correct subdirectories
COPY backend/pyproject.toml backend/poetry.lock ./backend/
COPY kurisu_core ./kurisu_core/

# Set the working directory to where pyproject.toml is
WORKDIR /opt/kurisu/backend

# Now the relative path `../kurisu_core` in pyproject.toml is valid!
# No `sed` command is needed.
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --without dev --no-root


# ---- Final Stage ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgthread-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kurisu/backend

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/kurisu/backend/.venv ./.venv

# Activate the virtual environment
ENV PATH="/opt/kurisu/backend/.venv/bin:$PATH"

# Copy the application source code
COPY backend/. .
COPY kurisu_core ../kurisu_core/

RUN useradd --create-home --shell /bin/bash backend && \
    chown -R backend:backend /opt/kurisu
USER backend

ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "uvicorn_log_config.json", "--reload"]