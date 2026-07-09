FROM python:3.11-slim

ENV OMP_NUM_THREADS=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY runbooks/ ./runbooks/

RUN mkdir -p /app/logs /app/data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
