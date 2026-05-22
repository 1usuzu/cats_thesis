from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import time

from metrics_cache import metrics_cache
from toxiproxy_reader import start_toxiproxy_reader
from compute_reader import start_compute_reader
from strategic_agent import start_strategic_agent
from tactical_agent import compute_cats_score, check_opa_safety

app = FastAPI(title="CATS Orchestrator Service (Tier-2 with OPA)")

class RouteRequest(BaseModel):
    prompt: str
    request_tag: str = "default"

@app.on_event("startup")
def startup_event():
    print("Khởi động bộ máy thu thập Control Plane...")
    start_toxiproxy_reader()
    start_compute_reader()
    start_strategic_agent() # Bật Tier-1 chạy ngầm mỗi 30s
    time.sleep(2)

@app.post("/route")
async def get_routing_decision(req: RouteRequest):
    start_time = time.time()
    
    cloud_score = compute_cats_score("cloud", req.request_tag)
    edge_score = compute_cats_score("edge", req.request_tag)
    
    preferred_site = "cloud" if cloud_score >= edge_score else "edge"
    backup_site = "edge" if preferred_site == "cloud" else "cloud"
    
    allow, violations = check_opa_safety(preferred_site, req.request_tag)
    decision = preferred_site
    opa_status = violations
    
    if not allow:
        backup_allow, backup_violations = check_opa_safety(backup_site, req.request_tag)
        if backup_allow:
            decision = backup_site
            opa_status = backup_violations
        else:
            decision = "cloud"
            opa_status = violations + backup_violations + ["FORCE_CLOUD_FALLBACK"]
            
    decision_time_ms = round((time.time() - start_time) * 1000, 2)
    
    return {
        "decision": decision,
        "cats_scores": {"cloud": cloud_score, "edge": edge_score},
        "opa_violations": opa_status,
        "decision_time_ms": decision_time_ms
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
