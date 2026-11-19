FROM python:3.12-slim-bookworm AS wheels
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY deploy/english/requirements.txt /tmp/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 ANONYMIZED_TELEMETRY=False
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY --from=wheels /wheels /tmp/wheels
COPY deploy/english/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt && rm -rf /tmp/wheels
COPY src/ src/
COPY frontend/english.html frontend/english.html
COPY data/source_contexts.json data/source_reading_notes.json data/
COPY scripts/english_pilot.py scripts/review_english_pilot.py scripts/
COPY english-pilot.env.example .
COPY deploy/english/start.py deploy/english/start.py
CMD ["python", "deploy/english/start.py"]
