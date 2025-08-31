
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*


COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kurisu_core ./kurisu_core
RUN pip install --no-cache-dir ./kurisu_core

COPY bot/. .


RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /app
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "main.py"]
