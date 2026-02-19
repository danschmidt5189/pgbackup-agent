FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        mariadb-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/

RUN pip install --no-cache-dir -e .

RUN pip install --no-cache-dir pytest pytest-cov ruff

COPY tests/ tests/

CMD ["pgbackup"]
