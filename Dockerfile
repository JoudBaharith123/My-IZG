# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY docs/ docs/
COPY psd/ psd/
COPY data/ data/
COPY *.md ./
COPY start_server.py ./
COPY Procfile ./

EXPOSE 8000

# Use PORT environment variable if set, otherwise default to 8000
ENV PORT=8000

CMD ["python", "start_server.py"]
