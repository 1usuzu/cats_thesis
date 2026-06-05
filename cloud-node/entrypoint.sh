#!/bin/bash
# Khởi động Ollama server nền
ollama serve &
SERVER_PID=$!

# Chờ server sẵn sàng
echo "Waiting for Ollama server..."
until ollama list > /dev/null 2>&1; do
  sleep 2
done

# Pull model (skip nếu đã có trong volume)
echo "Pulling Qwen2.5-7B..."
ollama pull qwen2.5:7b

# Warmup: load model vào VRAM
echo "Warming up model..."
ollama run qwen2.5:7b "hello" > /dev/null 2>&1

echo "Cloud-node ready."
wait $SERVER_PID
