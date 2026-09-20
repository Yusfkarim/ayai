FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python3 -m playwright install --with-deps chromium

COPY package.json ./
COPY main.py .
COPY easemate_client.mjs .
COPY easemate_sign.wasm .
COPY anakin_client.mjs .
COPY anakin_objecthash.js .
COPY model_sync.json .
COPY deepai_client.mjs .
COPY README.md .
RUN npm install --omit=dev --no-audit --no-fund

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "main.py"]
