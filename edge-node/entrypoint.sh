#!/bin/bash
ollama serve &
SERVER_PID=$!

until ollama list > /dev/null 2>&1; do sleep 2; done

# Pull cả 2 models (Inference + Strategic Agent)
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:1.5b-instruct

# Warmup cả 2 models vào RAM máy tính
ollama run qwen2.5:1.5b "hello" > /dev/null 2>&1
ollama run qwen2.5:1.5b-instruct "hello" > /dev/null 2>&1

echo "Edge-node ready (both models loaded)."
wait $SERVER_PID
