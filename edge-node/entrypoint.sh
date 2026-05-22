#!/bin/bash
ollama serve &
SERVER_PID=$!

until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do sleep 2; done

# Pull cả 2 models (Inference + Strategic Agent)
ollama pull qwen2.5:1.8b-q4_K_M
ollama pull qwen2.5:1.5b-instruct

# Warmup cả 2 models vào RAM máy tính
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:1.8b-q4_K_M","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:1.5b-instruct","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

echo "Edge-node ready (both models loaded)."
wait $SERVER_PID
