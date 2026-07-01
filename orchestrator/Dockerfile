FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install OPA CLI for Critic Agent validation
RUN curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/v0.61.0/opa_linux_amd64_static && \
    chmod +x /usr/local/bin/opa

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
