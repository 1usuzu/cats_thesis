from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import time
import os
import itertools
import uvicorn

app = FastAPI(title="CATS Ingress Gateway")

# Đọc cấu hình chiến lược từ hệ điều hành (Mặc định là PROPOSED của luận văn)
STRATEGY = os.getenv("BENCHMARK_STRATEGY", "PROPOSED")

ORCHESTRATOR_URL = "http://localhost:8080/route"
CLOUD_URL = "http://localhost:8001/api/generate"  # Qua Toxiproxy
EDGE_URL = "http://localhost:8002/api/generate"   # Qua Toxiproxy

# Dùng cho chiến lược BASELINE-1 (Round-Robin)
rr_counter = itertools.cycle(["cloud", "edge"])

class ChatRequest(BaseModel):
    prompt: str
    request_tag: str = "default"

@app.post("/chat")
async def chat(req: ChatRequest):
    decision = "cloud"
    
    # --- BƯỚC 1: XÁC ĐỊNH NODE ĐÍCH THEO CHIẾN LƯỢC ---
    if STRATEGY == "PROPOSED":
        # Gọi Orchestrator (CATS + OPA)
        async with httpx.AsyncClient() as client:
            res = await client.post(ORCHESTRATOR_URL, json={"prompt": req.prompt, "request_tag": req.request_tag})
            decision = res.json().get("decision", "cloud")
    elif STRATEGY == "BASELINE-1":
        decision = next(rr_counter)
    elif STRATEGY == "BASELINE-2":
        decision = "cloud"
    elif STRATEGY == "BASELINE-3":
        decision = "edge"

    # --- BƯỚC 2: CHUYỂN TIẾP (FORWARD) XUỐNG DATA PLANE ---
    target_url = CLOUD_URL if decision == "cloud" else EDGE_URL
    model_name = "qwen2.5:7b" if decision == "cloud" else "qwen2.5:1.5b"
    
    payload = {
        "model": model_name,
        "prompt": req.prompt,
        "stream": False
    }

    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(target_url, json=payload)
            response.raise_for_status()
            ttft_ms = round((time.time() - start_time) * 1000)
            data = response.json()
            
            return {
                "strategy_used": STRATEGY,
                "routed_to": decision,
                "ttft_ms": ttft_ms,
                "response": data.get("response")
            }
    except Exception as e:
        return {"error": f"Lỗi gọi LLM: {str(e)}"}

if __name__ == "__main__":
    print(f"Gateway đang chạy với chiến lược: {STRATEGY}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
