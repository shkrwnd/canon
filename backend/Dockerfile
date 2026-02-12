# Use Python 3.12 for prebuilt wheels (tiktoken, pydantic-core).
FROM python:3.12-slim

WORKDIR /app

# Upgrade pip so it prefers prebuilt binary wheels (avoids building tiktoken from source).
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
