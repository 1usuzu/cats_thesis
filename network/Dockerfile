FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir requests
COPY . .
CMD ["python", "init_proxies.py"]
