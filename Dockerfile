FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements_v2.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY src/ ./src/

COPY scripts/ ./scripts/


# Data directory
RUN mkdir -p /app/data

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["python", "-m", "src.main"]
