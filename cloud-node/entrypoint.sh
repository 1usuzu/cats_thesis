#!/bin/bash
# Khởi động Ollama server nền
ollama serve &
SERVER_PID=$!

# Chờ server sẵn sàng
echo "Waiting for Ollama server..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
done

# Pull model (skip nếu đã có trong volume)
echo "Pulling Qwen2.5-7B-Q4_K_M..."
ollama pull qwen2.5:7b-q4_K_M

# Warmup: load model vào VRAM
echo "Warming up model..."
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b-q4_K_M","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

echo "Cloud-node ready."
wait $SERVER_PID
