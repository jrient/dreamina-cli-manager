# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dreamina binary
# Option A: copy pre-downloaded binary (recommended for air-gapped envs)
COPY dreamina /usr/local/bin/dreamina
RUN chmod +x /usr/local/bin/dreamina

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]