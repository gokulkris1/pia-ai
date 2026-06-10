FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend
COPY users users
COPY persona persona

CMD ["sh", "-c", "uvicorn main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
