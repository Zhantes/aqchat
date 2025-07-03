FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y curl git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
COPY . .

ENV PATH="/venv/bin:$PATH"

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
