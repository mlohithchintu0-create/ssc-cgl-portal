FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python seed_data.py

EXPOSE 5000

CMD ["gunicorn", "app:app", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:5000", "--timeout", "120"]
