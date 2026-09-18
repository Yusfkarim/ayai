FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests

COPY main.py .
COPY easemate_client.mjs .
COPY easemate_sign.wasm .
COPY deepai_client.mjs .
COPY README.md .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "main.py"]
