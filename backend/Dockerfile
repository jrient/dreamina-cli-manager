# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies for dreamina
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dreamina CLI from official source
RUN curl -fsSL https://jimeng.jianying.com/cli | bash

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]