FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY requirements-dev.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

COPY app/ app/
COPY tests/ tests/
COPY scripts/ scripts/

CMD ["python", "app/main.py"]