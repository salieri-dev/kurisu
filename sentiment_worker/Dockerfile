
FROM kurisu-sentiment-base:latest as final

RUN useradd --create-home --shell /bin/bash app

WORKDIR /opt/kurisu/sentiment_worker

COPY --chown=app:app kurisu_core ../kurisu_core/
COPY --chown=app:app sentiment_worker/. .

USER app

CMD ["python", "main.py"]