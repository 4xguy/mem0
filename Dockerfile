FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=0

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install mem0 with optional extras required by the API server.
COPY pyproject.toml poetry.lock README.md ./
COPY mem0 ./mem0
RUN pip install --upgrade pip \
    && pip install ".[llms]" "psycopg[binary]>=3.2.8" "psycopg-pool>=3.2.6" "pgvector>=0.3.6" "redis>=5.0.0,<6.0.0"

# Install FastAPI server dependencies.
RUN pip install fastapi==0.115.8 uvicorn[standard]==0.34.0 python-dotenv==1.0.1 pydantic==2.10.4

# Copy API server code.
COPY server /app/server

WORKDIR /app/server

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
