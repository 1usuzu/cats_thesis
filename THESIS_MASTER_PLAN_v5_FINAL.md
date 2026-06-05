# THESIS MASTER PLAN — v5.0 FINAL
## "Hệ thống điều phối suy luận LLM ở biên theo điều hướng lưu lượng thích nghi tài nguyên (CATS)"
### Phiên bản hoàn chỉnh cuối cùng — Tháng 5/2026

---

## CHANGELOG ĐẦY ĐỦ

| Phiên bản | Lỗi đã sửa |
|---|---|
| v1.0 | Bản gốc — 3 lỗ hổng cơ bản |
| v2.0 | Fix OOM, LLM arithmetic, bandwidth probe |
| v3.0 | Fix compute isolation → 2 Ollama containers |
| v4.0 | Fix môi trường WSL2 → Ubuntu; Toxiproxy primary; bỏ model swap |
| v5.0 | Fix 12 lỗi mới: packet_loss metric, RTT measurement, KEEP_ALIVE, NUM_PARALLEL VRAM, Prometheus staleness, model warmup, experiment isolation, model pull, OPA schema, ROUGE-L collection, baseline switching, CPU isolation |

---

## BẢN ĐỒ CÁC LỖI ĐÃ XỬ LÝ TRONG v5.0

| # | Lỗi | Mức độ | Fix |
|---|---|---|---|
| 1 | OLLAMA_NUM_PARALLEL thiếu → queue nổ tung ở HIGH load | Nghiêm trọng | Thêm vào docker-compose, cloud=2, edge=2 |
| 2 | CPU isolation thiếu → Control Plane tranh CPU Data Plane | Quan trọng | cpuset trong docker-compose |
| 3 | Metrics collector đi qua Toxiproxy → bị inject delay | Quan trọng | 2 URL set riêng biệt trong .env |
| 4 | `cats_network_packet_loss_pct` bất khả thi với Toxiproxy | **Nghiêm trọng** | Xóa khỏi metric schema và CATS formula |
| 5 | ICMP RTT ≈ 0ms vì cùng Docker host → metric vô nghĩa | **Nghiêm trọng** | Thay bằng Toxiproxy declared latency |
| 6 | OLLAMA_KEEP_ALIVE thiếu → model unload sau 5 phút idle | Nghiêm trọng | Thêm KEEP_ALIVE=-1 vào docker-compose |
| 7 | Prometheus 15s scrape interval → routing decisions stale | Quan trọng | Tactical Agent dùng in-memory cache |
| 8 | OLLAMA_NUM_PARALLEL=4 cloud → VRAM risk trên 8GB card | Quan trọng | cloud=2 (safer) + KV cache quantization |
| 9 | Model warmup thiếu → cold start vài giây đầu | Quan trọng | Thêm warmup task vào Phase 1 |
| 10 | Experiment isolation giữa 24 runs không xác định | Quan trọng | Thêm reset procedure |
| 11 | Ollama model pull trong Dockerfile không khả thi | Quan trọng | Entrypoint startup script |
| 12 | OPA input schema không xác định | Quan trọng | Định nghĩa rõ JSON schema |
| 13 | ROUGE-L paired collection không xác định | Quan trọng | Thêm dual-route sampling |
| 14 | Baseline strategy switching không xác định | Quan trọng | Thêm BENCHMARK_STRATEGY env/API |
| 15 | IF/ELSE academic defense chưa chuẩn bị | Học thuật | Thêm vào Chapter 6 outline |

---

## PHẦN 1 — MÔI TRƯỜNG PHẦN CỨNG

### 1.1 Môi trường bắt buộc

**Primary: Ubuntu 22.04 LTS native (dual-boot hoặc dedicated)**
- tc/netem, Docker Engine, CUDA driver hoạt động trực tiếp, không overhead
- Nếu bắt buộc dùng Windows: Toxiproxy thay tc/netem (đã dùng rồi) — không ảnh hưởng kiến trúc

### 1.2 Cấu hình phần cứng

```
OS:     Ubuntu 22.04 LTS native
RAM:    ≥ 12 GB (16 GB khuyến nghị)
GPU:    RTX 4060 — 8 GB VRAM
CPU:    8 cores
Disk:   ≥ 60 GB free
```

### 1.3 RAM/VRAM Budget (v5.0 — confirmed)

| Thành phần | RAM | VRAM | Ghi chú |
|---|---|---|---|
| cloud-node: Qwen2.5-7B-Q4_K_M | ~0.5 GB | ~4.5 GB | Weights |
| cloud-node: KV cache (2 parallel × 4096 ctx) | 0 | ~0.8 GB | FP16→q8_0: ~0.4 GB |
| edge-node: Qwen2.5-1.8B-Q4 | ~1.2 GB | 0 | Inference model |
| edge-node: Qwen2.5-1.5B-instruct | ~1.5 GB | 0 | Strategic agent |
| edge-node: KV cache (2 parallel) | ~0.2 GB | 0 | CPU inference |
| Orchestration service | ~0.3 GB | 0 | |
| OPA server | ~0.1 GB | 0 | |
| Toxiproxy | ~0.1 GB | 0 | |
| Prometheus + OTel + Grafana | ~0.8 GB | 0 | |
| OS + Ubuntu overhead | ~1.5 GB | 0 | Ít hơn WSL2 |
| Buffer an toàn | ~3.5 GB | ~2.3 GB | |
| **TỔNG (12 GB host)** | **~6.2 GB ✅** | **~5.7 GB ✅** | Đủ thoải mái |

**Lý do cloud NUM_PARALLEL=2 thay vì 4:**
RTX 4060 8GB → weights 4.5GB + KV cache với 4 slots ≈ 1.6GB → tổng 6.1GB → chỉ còn 1.9GB buffer. Với context dài hơn hoặc system overhead, sẽ chạm giới hạn. NUM_PARALLEL=2 → KV cache ≈ 0.4GB (q8_0) → tổng 5.7GB → buffer 2.3GB — an toàn.

---

## PHẦN 2 — BÀI TOÁN VÀ CONTRIBUTION

### 2.1 Research Gap

Các hệ thống LLM routing hiện tại (RouteLLM, vLLM Semantic Router, NotDiamond) route theo **query complexity** hoặc **model capability**. Không ai route theo **network + compute conditions** với IETF-compliant metrics. Khoảng trống này là nền tảng học thuật của luận văn.

### 2.2 Contributions (5 điểm, không thay đổi)

1. CATS-native LLM telemetry schema (passive-measured vs declared-from-emulation)
2. Two-tier Agentic Orchestrator (Tier-1: Strategic PRA loop; Tier-2: Tactical reactive)
3. Heterogeneous site routing với quality dimension (GPU cloud vs CPU edge)
4. LLM-as-Classifier accuracy benchmark vs rule-based
5. Quality-latency trade-off measurement (ROUGE-L)

### 2.3 Agentic Framing chuẩn cho báo cáo

```
Tier-1 Strategic Agent — Perception → Reasoning → Action (30s loop):
  PERCEIVE:  Aggregate telemetry window → structured JSON
  REASON:    Qwen2.5-1.5B-instruct classify → 1 trong 5 system states
  ACT:       Lookup template → publish sang Tier-2 shared state
  FALLBACK:  Rule-based nếu LLM output invalid

Tier-2 Tactical Agent — Reactive Execution (per-request, <10ms):
  READ:      current_template từ shared state
  COMPUTE:   CATS score cho mỗi site
  ENFORCE:   OPA policy check
  ROUTE:     Forward đến site tốt nhất
```

### 2.4 Chuẩn bị câu trả lời "Tại sao không dùng IF/ELSE?" (viết vào Chapter 6)

Ba lớp lập luận cần chuẩn bị:

**Lớp 1 — Extensibility:** Trong prototype, telemetry là số cấu trúc nên IF/ELSE đủ dùng. Nhưng kiến trúc agentic chứng minh khả năng mở rộng: khi telemetry bao gồm unstructured text (log lỗi "Thermal throttling detected", "CUDA OOM on layer 24"), LLM đọc được ngữ cảnh mà IF/ELSE tĩnh không thể.

**Lớp 2 — Empirical evidence:** Luận văn đo accuracy = X% (≥85%) trên 100 snapshots. Đây là kết quả thực nghiệm về khả năng classification, không phải giả thuyết. Kết quả này justify việc dùng LLM.

**Lớp 3 — Proactive acknowledgment:** Chủ động viết trong Limitations: "The structured nature of the current metric schema allows a deterministic classifier to achieve 100% accuracy. The LLM-based classifier is validated as a proof-of-concept demonstrating architectural extensibility toward semantic telemetry interpretation."

---

## PHẦN 3 — KIẾN TRÚC HỆ THỐNG (v5.0)

### 3.1 Sơ đồ tổng thể

```
┌──────────────────────────────────────────────────────────────────────┐
│                  UBUNTU 22.04 HOST (≥12GB RAM, RTX 4060)             │
│                                                                      │
│  ┌───────────────────────┐    ┌─────────────────────────────────┐   │
│  │  cloud-node (Docker)  │    │  edge-node (Docker)             │   │
│  │  cpuset: 0-5 (shared) │    │  cpuset: 0-5 (shared)          │   │
│  │                       │    │                                 │   │
│  │  Ollama :11434        │    │  Ollama :11435                  │   │
│  │  Model: Qwen2.5-7B-Q4 │    │  Model A: Qwen2.5-1.8B-Q4     │   │
│  │  Backend: GPU RTX4060 │    │  Model B: Qwen2.5-1.5B-instruct│   │
│  │  NUM_PARALLEL: 2      │    │  (cả 2 luôn loaded)            │   │
│  │  KEEP_ALIVE: -1       │    │  NUM_PARALLEL: 2               │   │
│  │  KV_CACHE: q8_0       │    │  KEEP_ALIVE: -1                │   │
│  │  VRAM: ~5.3GB ✅      │    │  MAX_LOADED_MODELS: 2          │   │
│  └──────────┬────────────┘    └────────────────┬────────────────┘   │
│             │ DATA PLANE only                  │ DATA PLANE only    │
│  ┌──────────▼──────────────────────────────────▼────────────────┐   │
│  │  TOXIPROXY :8474 (API) | :8001 cloud-proxy | :8002 edge-proxy│   │
│  │  Injects: latency + bandwidth (thay cho packet loss)         │   │
│  │  REST API → declared metrics → MetricsCache (Python)         │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │  ORCHESTRATION SERVICE :8080 — cpuset: 6-7 (dedicated)      │   │
│  │                                                              │   │
│  │  MetricsCache (in-memory, cập nhật 2s):                     │   │
│  │    - Toxiproxy API → declared: latency_ms, bandwidth_kbps   │   │
│  │    - Ollama /api/ps → queue_depth (CONTROL PLANE, direct)   │   │
│  │    - /proc/stat → cpu_util (CONTROL PLANE, direct)          │   │
│  │    - nvidia-smi → gpu_util (CONTROL PLANE, direct)          │   │
│  │    - FastAPI middleware → ttft_ms per site                   │   │
│  │                                                              │   │
│  │  ┌────────────────────────┐  ┌──────────────────────────┐   │   │
│  │  │  Tier-2 TACTICAL AGENT│  │  Tier-1 STRATEGIC AGENT  │   │   │
│  │  │  per-request, <10ms   │  │  30s loop                │   │   │
│  │  │  Đọc MetricsCache     │◄─│  Đọc MetricsCache        │   │   │
│  │  │  Tính CATS score      │  │  Gọi Qwen2.5-1.5B        │   │   │
│  │  │  OPA policy check     │  │  Classify → template      │   │   │
│  │  │  Return route decision│  │  Publish shared state     │   │   │
│  │  └────────────────────────┘  └──────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │  CATS INGRESS GATEWAY :8000 (FastAPI)                        │   │
│  │  → PROPOSED: gọi Orchestrator, nhận route, forward Toxiproxy │   │
│  │  → BASELINE-1/2/3: hardcoded routing (env BENCHMARK_STRATEGY)│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             ▲                                       │
│               Locust load generator (local process)                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TELEMETRY (visualization only — NOT used for routing)       │   │
│  │  Prometheus :9090 ← MetricsCache push mỗi 5s                │   │
│  │  Grafana :3000 ← Prometheus datasource                       │   │
│  │  OTel Collector ← Gateway traces (optional)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  OPA Server :8181  [5 Rego rules]                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Nguyên tắc routing rõ ràng (Fix lỗi #3)

**DATA PLANE** (bị inject delay): Gateway → Toxiproxy → Ollama
**CONTROL PLANE** (KHÔNG qua Toxiproxy): MetricsCache → Ollama trực tiếp

```
# .env — Hai bộ URL hoàn toàn tách biệt
# DATA PLANE: qua Toxiproxy (bị inject network conditions)
CLOUD_INFERENCE_URL=http://toxiproxy:8001
EDGE_INFERENCE_URL=http://toxiproxy:8002

# CONTROL PLANE: trực tiếp đến Ollama (không bị delay)
CLOUD_METRICS_URL=http://cloud-node:11434
EDGE_METRICS_URL=http://edge-node:11435
STRATEGIC_AGENT_URL=http://edge-node:11435
```

### 3.3 CATS Metric Schema (v5.0 — loại bỏ packet_loss)

**PASSIVE-MEASURED (CONTROL PLANE, không qua Toxiproxy):**

| Metric | Nguồn | Interval |
|---|---|---|
| `cats_compute_queue_depth[site]` | `GET {METRICS_URL}/api/ps` | 500ms |
| `cats_compute_ttft_ms[site]` | FastAPI middleware | per-request |
| `cats_compute_gpu_util_pct` | `nvidia-smi` (cloud-node) | 2s |
| `cats_compute_cpu_util_pct` | `/proc/stat` delta (edge-node) | 2s |
| `cats_compute_mem_pressure_pct[site]` | `/proc/meminfo` | 2s |

**DECLARED-FROM-EMULATION (Toxiproxy REST API):**

| Metric | Nguồn | Ghi chú |
|---|---|---|
| `cats_network_latency_ms[site]` | `GET /proxies/{name}/toxics` → latency.latency | **Dùng làm RTT trong CATS score** |
| `cats_network_jitter_ms[site]` | `GET /proxies/{name}/toxics` → latency.jitter | |
| `cats_network_bandwidth_kbps[site]` | `GET /proxies/{name}/toxics` → bandwidth.rate × 8 / 1000 | rate là bytes/s |

**Metrics đã XÓA khỏi v5.0 và lý do:**
- ~~`cats_network_rtt_ms`~~ → ICMP trên Docker bridge = 0ms, vô nghĩa. Thay bằng `cats_network_latency_ms` từ Toxiproxy
- ~~`cats_network_packet_loss_pct`~~ → Toxiproxy không có packet loss toxic. Không thể đo chính xác

**Ghi chú thesis về packet loss:** *"Toxiproxy does not natively support randomized packet-level loss simulation, which requires kernel-level traffic shaping (tc/netem). This limitation is acknowledged; the BAD network profile instead employs severe bandwidth throttling (250 Kbps) and high latency (350ms) to represent degraded network conditions, which are equally representative of poor WAN links."*

### 3.4 CATS Scoring Formula (v5.0 — cập nhật)

```
cats_score(site) =
    W_LATENCY   × (1 / (1 + latency_ms / 100))
  + W_QUEUE     × (1 - queue_depth / MAX_QUEUE)
  + W_COMPUTE   × (1 - compute_util / 100)
  + W_QUALITY   × model_quality_score

Weights (default):
  W_LATENCY=0.30, W_QUEUE=0.30, W_COMPUTE=0.25, W_QUALITY=0.15

Thay đổi từ v4.0:
  - Đổi tên W_RTT → W_LATENCY (metric dùng là declared latency, không phải ICMP RTT)
  - Xóa penalty: "- 0.5 if packet_loss > THRESHOLD" (metric không thể đo)
  - Bandwidth ảnh hưởng gián tiếp: bandwidth thấp → TTFT cao → queue tăng → CATS score giảm tự nhiên

Request tag override:
  "fast_ok":      W_QUALITY → 0.05
  "high_quality": W_QUALITY → 0.30

model_quality_score:
  Qwen2.5-7B (cloud)  → 1.0
  Qwen2.5-1.8B (edge) → 0.6
```

### 3.5 Tier-1 System States (v5.0 — cập nhật)

```python
# Xóa packet_loss khỏi STATE_DEGRADED, thay bằng bandwidth
STATE_NORMAL:       latency < 80ms, queue < 20, compute < 70%, bandwidth > 5000 kbps
STATE_EDGE_LOADED:  edge queue_depth > 35 OR edge cpu_util > 85%
STATE_DEGRADED:     latency > 150ms OR bandwidth_kbps < 1000 (bất kỳ site nào)
STATE_BURST:        current_rps > 1.5× previous_rps
STATE_CRITICAL:     ≥ 2 conditions above simultaneously

ROUTING_TEMPLATES = {
    "STATE_NORMAL":       {"cloud": 0.50, "edge": 0.50},
    "STATE_EDGE_LOADED":  {"cloud": 0.75, "edge": 0.25},
    "STATE_DEGRADED":     {"cloud": 0.40, "edge": 0.60},
    "STATE_BURST":        {"cloud": 0.65, "edge": 0.35},
    "STATE_CRITICAL":     {"cloud": 0.90, "edge": 0.10},
}
```

**Tier-1 LLM Prompt (cập nhật — bỏ packet_loss):**
```
You are a system state classifier for an LLM inference orchestrator.
Read the telemetry summary and output EXACTLY ONE state label.

Valid outputs (one word only):
  STATE_NORMAL | STATE_EDGE_LOADED | STATE_DEGRADED | STATE_BURST | STATE_CRITICAL

Rules:
- STATE_EDGE_LOADED: edge queue_depth > 35 OR edge cpu_util > 85
- STATE_DEGRADED: any latency_ms > 150 OR any bandwidth_kbps < 1000
- STATE_BURST: current_rps > 1.5 × previous_rps
- STATE_CRITICAL: two or more of the above conditions apply
- STATE_NORMAL: none of the above

Telemetry:
{telemetry_json}

Output the state label only.
```

### 3.6 OPA Input Schema (v5.0 — định nghĩa rõ, Fix lỗi #12)

```json
// POST http://opa:8181/v1/data/routing/allow
// Input JSON gửi từ Tactical Agent:
{
  "input": {
    "site": "cloud",
    "queue_depth": 45,
    "compute_util": 88.5,
    "predicted_latency_ms": 520,
    "request_tag": "high_quality",
    "site_state": "DEGRADED",
    "sla_target_ms": 500
  }
}
// OPA trả về: {"result": {"allow": true/false, "reason": "..."}}
```

### 3.7 Safety Gate (OPA — 5 Rules, cập nhật ngưỡng)

```
RULE 1: queue_depth > 50                                     → reject site
RULE 2: compute_util > 90% (GPU) hoặc > 92% (CPU)           → reject site
RULE 3: predicted_latency_ms > sla_target_ms                → reject + try other site
RULE 4: tất cả sites rejected                               → force cloud (last resort)
RULE 5: request_tag == "high_quality" AND site_state == "DEGRADED" AND site == "edge"
        → reject edge
```

---

## PHẦN 4 — NETWORK EMULATION (v5.0)

### 4.1 3 Network Profiles (cập nhật — thay packet_loss)

**PROFILE GOOD:**
```json
cloud-proxy: { "latency": 15, "jitter": 3, "bandwidth_kbps": 100000 }
edge-proxy:  { "latency": 5,  "jitter": 1, "bandwidth_kbps": 100000 }
```

**PROFILE MEDIUM:**
```json
cloud-proxy: { "latency": 120, "jitter": 25, "bandwidth_kbps": 10000 }
edge-proxy:  { "latency": 30,  "jitter": 5,  "bandwidth_kbps": 50000 }
```

**PROFILE BAD:**
```json
cloud-proxy: { "latency": 350, "jitter": 60, "bandwidth_kbps": 250  }
edge-proxy:  { "latency": 80,  "jitter": 15, "bandwidth_kbps": 1000 }
```

**Lưu ý kỹ thuật về bandwidth toxic:** Toxiproxy bandwidth rate đơn vị là bytes/second.
- 100 Mbps = 12,500,000 bytes/s → `"rate": 12500000`
- 10 Mbps  = 1,250,000 bytes/s  → `"rate": 1250000`
- 250 Kbps = 31,250 bytes/s     → `"rate": 31250`
- 1 Mbps   = 125,000 bytes/s    → `"rate": 125000`

### 4.2 Toxiproxy Config Reader

Script query `GET http://toxiproxy:8474/proxies/{name}/toxics` mỗi 5s, parse JSON:
```
latency_ms   = toxics["latency_downstream"]["attributes"]["latency"]
jitter_ms    = toxics["latency_downstream"]["attributes"]["jitter"]
bandwidth_bps = toxics["bandwidth_downstream"]["attributes"]["rate"]
bandwidth_kbps = bandwidth_bps × 8 / 1000
```
Lưu vào MetricsCache. Nếu không có toxic → latency=0, bandwidth=100000 (GOOD default).

---

## PHẦN 5 — BENCHMARK METHODOLOGY

### 5.1 Ma trận thử nghiệm (24 experiments)

```
3 network profiles × 2 load levels × 4 strategies = 24 experiments
Mỗi experiment: 5 phút + 30s warm-up bỏ qua
```

### 5.2 4 Strategies và cách switching (Fix lỗi #14)

Gateway đọc env `BENCHMARK_STRATEGY` khi khởi động:

```
PROPOSED:   Full two-tier orchestrator (Tier-1 + Tier-2 + OPA)
BASELINE-1: Round-robin (counter % 2 → cloud hoặc edge, xen kẽ)
BASELINE-2: Always cloud (mọi request → Toxiproxy cloud-proxy → cloud-node)
BASELINE-3: Always edge  (mọi request → Toxiproxy edge-proxy  → edge-node)
```

Benchmark script đặt `BENCHMARK_STRATEGY` trong `docker-compose.override.yml` hoặc env trước khi restart gateway. Gateway không cần restart toàn bộ stack.

### 5.3 Dataset

**Nguồn:** HuggingFace `anon8231489123/ShareGPT_Vicuna_unfiltered` hoặc subset tương đương
**Preprocessing:**
- Lấy 500 conversations đầu tiên, seed=42
- Chỉ lấy human turn đầu tiên của mỗi conversation
- Truncate về ≤ 1024 tokens (tránh OOM, giữ inference time hợp lý)
- Save thành `benchmark/prompts/sharegpt_500.json`

### 5.4 ROUGE-L Paired Collection (Fix lỗi #13)

Để tính ROUGE-L cần response từ CẢ HAI nodes trên cùng 1 prompt.

Giải pháp: **Dual-route sampling mode** — gateway có endpoint đặc biệt `POST /quality-sample` gửi cùng 1 prompt song song đến cả cloud và edge, collect cả 2 responses, tính ROUGE-L ngay.

Procedure trong Phase 8:
- Chạy 100 prompts qua `/quality-sample` (không tính vào benchmark latency)
- Mỗi call: gửi đến cloud-node và edge-node, record cả 2 responses
- Tính ROUGE-L (cloud response = reference, edge response = hypothesis)
- Chạy sau khi toàn bộ 24 experiments xong, dùng MEDIUM profile, LOW load

### 5.5 Experiment Isolation Procedure (Fix lỗi #10)

Giữa mỗi experiment trong `run_all.py`:
```
1. Chờ Locust kết thúc
2. Sleep 30s (drain Ollama queue)
3. Verify: cả 2 Ollama queue_depth == 0
4. Reset Toxiproxy: xóa toxics cũ, apply profile mới
5. Verify: declared metrics cập nhật đúng
6. Set BENCHMARK_STRATEGY mới (nếu thay đổi)
7. Restart gateway (nhẹ, chỉ container gateway, ~5s)
8. Trigger model warmup: gửi 1 dummy prompt đến mỗi node
9. Sleep 10s stabilize
10. Bắt đầu experiment mới
```

---

## PHẦN 6 — STACK CÔNG NGHỆ

| Component | Tool | Version |
|---|---|---|
| Inference GPU | Ollama + CUDA | Latest stable |
| Inference CPU | Ollama CPU | Latest stable |
| Network emulation | Toxiproxy | 2.12+ |
| Gateway | FastAPI | 0.110+ |
| Orchestrator | Python | 3.11 |
| Policy engine | OPA | 0.68+ |
| Telemetry | Prometheus + Grafana | Latest stable |
| Load test | Locust | 2.x |
| ROUGE-L | `rouge-score` Python lib | 0.1.2 |
| Analysis | pandas + matplotlib | Latest stable |

---

## PHẦN 7 — CẤU TRÚC THƯ MỤC

```
cats-llm-orchestrator/
├── docker-compose.yml            # Stack chính
├── docker-compose.override.yml   # Benchmark strategy override
├── .env                          # Cấu hình đầy đủ
│
├── cloud-node/
│   ├── Dockerfile
│   └── entrypoint.sh             # ← QUAN TRỌNG: pull model tại runtime
│
├── edge-node/
│   ├── Dockerfile
│   └── entrypoint.sh             # pull cả 2 models + warmup
│
├── gateway/
│   ├── main.py                   # FastAPI + strategy routing + TTFT middleware
│   ├── quality_sample.py         # ROUGE-L dual-route endpoint
│   └── Dockerfile
│
├── orchestrator/
│   ├── metrics_cache.py          # In-memory cache, cập nhật 2s — KHÔNG dùng Prometheus
│   ├── toxiproxy_reader.py       # Declared metrics → MetricsCache
│   ├── tactical_agent.py         # Tier-2: CATS score + OPA check
│   ├── strategic_agent.py        # Tier-1: LLM classify + template publish
│   ├── routing_templates.py      # 5 templates
│   ├── shared_state.py           # Thread-safe template store
│   └── Dockerfile
│
├── safety/
│   └── policies/routing.rego     # 5 OPA rules với input schema đúng
│
├── network/
│   ├── toxiproxy_init.json       # Proxy definitions (populate endpoint)
│   └── profiles/
│       ├── good.py               # Apply GOOD profile via REST API
│       ├── medium.py
│       └── bad.py
│
├── telemetry/
│   ├── prometheus.yml
│   └── grafana/dashboards/cats-dashboard.json
│
├── benchmark/
│   ├── locustfile.py
│   ├── run_experiment.py         # 1 experiment + isolation procedure
│   ├── run_all.py                # 24 experiments automation
│   ├── prompts/sharegpt_500.json # Preprocessed dataset
│   └── results/                  # CSV exports
│
├── evaluation/
│   ├── snapshots/tier1_snapshots.json
│   ├── evaluate_tier1.py
│   └── rouge_eval.py             # Dùng `rouge-score` library
│
└── analysis/
    ├── plot_latency.py
    ├── plot_sla.py
    ├── plot_routing.py
    ├── plot_rouge.py
    └── export_tables.py
```

---

## PHẦN 8 — DOCKER COMPOSE CONFIGURATION (v5.0)

### 8.1 Các env vars Ollama bắt buộc

```yaml
# docker-compose.yml (excerpt)

cloud-node:
  image: ollama/ollama
  runtime: nvidia
  environment:
    - OLLAMA_NUM_PARALLEL=2        # Fix lỗi #1: tránh queue nổ tung
    - OLLAMA_MAX_QUEUE=50          # Fix lỗi #1
    - OLLAMA_KEEP_ALIVE=-1         # Fix lỗi #6: không unload model
    - OLLAMA_KV_CACHE_TYPE=q8_0    # Fix lỗi #8: tiết kiệm VRAM
  cpuset: "0,1,2,3,4,5"           # Fix lỗi #2: chia sẻ CPU với edge
  volumes:
    - cloud-models:/root/.ollama
  entrypoint: ["/entrypoint.sh"]   # Fix lỗi #11: pull model at runtime
  ports: ["11434:11434"]
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

edge-node:
  image: ollama/ollama
  environment:
    - OLLAMA_NUM_PARALLEL=2        # Fix lỗi #1
    - OLLAMA_MAX_QUEUE=50          # Fix lỗi #1
    - OLLAMA_KEEP_ALIVE=-1         # Fix lỗi #6
    - OLLAMA_MAX_LOADED_MODELS=2   # Cho phép 2 models cùng lúc trong RAM
  cpuset: "0,1,2,3,4,5"           # Chia sẻ 6 cores với cloud (CPU inference)
  volumes:
    - edge-models:/root/.ollama
  entrypoint: ["/entrypoint.sh"]   # pull + warmup cả 2 models
  ports: ["11435:11434"]

orchestrator:
  cpuset: "6,7"                    # Fix lỗi #2: 2 cores riêng cho control plane
  environment:
    - CLOUD_INFERENCE_URL=http://toxiproxy:8001    # Fix lỗi #3: DATA PLANE
    - EDGE_INFERENCE_URL=http://toxiproxy:8002
    - CLOUD_METRICS_URL=http://cloud-node:11434    # Fix lỗi #3: CONTROL PLANE
    - EDGE_METRICS_URL=http://edge-node:11435
    - STRATEGIC_AGENT_URL=http://edge-node:11435
    - PROMETHEUS_PUSH_URL=http://prometheus:9090   # Push only — không dùng để đọc

gateway:
  environment:
    - BENCHMARK_STRATEGY=PROPOSED   # Fix lỗi #14: override khi benchmark
    - ORCHESTRATOR_URL=http://orchestrator:8080
    - CLOUD_INFERENCE_URL=http://toxiproxy:8001
    - EDGE_INFERENCE_URL=http://toxiproxy:8002
```

### 8.2 Entrypoint Script Pattern (Fix lỗi #11)

`cloud-node/entrypoint.sh`:
```bash
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

# Warmup: load model vào VRAM (Fix lỗi #9)
echo "Warming up model..."
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b-q4_K_M","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

echo "Cloud-node ready."
wait $SERVER_PID
```

`edge-node/entrypoint.sh`:
```bash
#!/bin/bash
ollama serve &
SERVER_PID=$!

until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do sleep 2; done

# Pull cả 2 models
ollama pull qwen2.5:1.8b-q4_K_M
ollama pull qwen2.5:1.5b-instruct

# Warmup cả 2 models vào RAM (Fix lỗi #9)
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:1.8b-q4_K_M","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:1.5b-instruct","prompt":"hello","stream":false,"keep_alive":-1}' \
  > /dev/null

echo "Edge-node ready (both models loaded)."
wait $SERVER_PID
```

---

## PHẦN 9 — METRICS ARCHITECTURE (Fix lỗi #7)

### 9.1 MetricsCache — In-Memory, dùng cho routing

```
MetricsCache (Python dict, thread-safe với Lock):
  cloud_latency_ms:    [from Toxiproxy every 5s]
  cloud_jitter_ms:     [from Toxiproxy every 5s]
  cloud_bandwidth_kbps:[from Toxiproxy every 5s]
  cloud_queue_depth:   [from Ollama API direct every 500ms]
  cloud_gpu_util:      [from nvidia-smi every 2s]
  cloud_ttft_ms_avg:   [from Gateway middleware, rolling 30-req window]

  edge_latency_ms:     [from Toxiproxy every 5s]
  edge_jitter_ms:      [from Toxiproxy every 5s]
  edge_bandwidth_kbps: [from Toxiproxy every 5s]
  edge_queue_depth:    [from Ollama API direct every 500ms]
  edge_cpu_util:       [from /proc/stat every 2s]
  edge_ttft_ms_avg:    [from Gateway middleware, rolling 30-req window]

  current_rps:         [computed from Gateway request counter]
  previous_rps:        [epoch N-1 rps, updated mỗi 30s]
```

**Tactical Agent đọc trực tiếp từ MetricsCache** — không bao giờ query Prometheus API.
Prometheus nhận data push từ MetricsCache mỗi 5 giây, dùng cho visualization và historical logging.

### 9.2 Prometheus chỉ để visualize (không dùng cho routing)

Grafana panels:
- RTT/Latency (declared) — timeline
- Bandwidth (declared) — timeline
- Queue depth per site — timeline
- GPU/CPU utilization — timeline
- TTFT moving average — timeline
- SLA violation rate — gauge
- Routing distribution — pie chart

---

## PHẦN 10 — ROADMAP CHI TIẾT (v5.0)

> Mỗi phase có Acceptance Criteria. KHÔNG chuyển phase nếu chưa pass.

---

### PHASE 0 — Môi trường & Go/No-Go (Tuần 1, tháng 5)

#### Task 0.1 — Ubuntu setup
- [ ] Xác nhận Ubuntu 22.04 LTS native đang chạy: `lsb_release -a`
- [ ] Cài NVIDIA driver: `ubuntu-drivers autoinstall` → reboot → `nvidia-smi`
- [ ] Cài Docker Engine (official apt repo, không phải Docker Desktop)
- [ ] Cài NVIDIA Container Toolkit: `sudo nvidia-ctk runtime configure --runtime=docker`
- [ ] Thêm user vào docker group: `sudo usermod -aG docker $USER`

#### Task 0.2 — 5 Go/No-Go Tests bắt buộc

**TEST 1 — GPU in Docker:**
```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
# Expected: "RTX 4060", "8192 MiB"
```

**TEST 2 — Ollama GPU với model 7B:**
```bash
docker run --gpus all -p 11434:11434 \
  -e OLLAMA_NUM_PARALLEL=2 \
  -e OLLAMA_KEEP_ALIVE=-1 \
  -e OLLAMA_KV_CACHE_TYPE=q8_0 \
  -d ollama/ollama
docker exec <id> ollama pull qwen2.5:7b-q4_K_M
# Expected: VRAM tăng ~5.3GB (weights + KV cache q8_0)
# Verify: nvidia-smi → VRAM used ≤ 6GB sau khi warm up
```

**TEST 3 — Ollama CPU với 2 models:**
```bash
docker run -p 11435:11434 \
  -e OLLAMA_NUM_PARALLEL=2 \
  -e OLLAMA_KEEP_ALIVE=-1 \
  -e OLLAMA_MAX_LOADED_MODELS=2 \
  -d ollama/ollama
docker exec <id> ollama pull qwen2.5:1.8b-q4_K_M
docker exec <id> ollama pull qwen2.5:1.5b-instruct
# Warmup cả 2:
curl http://localhost:11435/api/generate -d '{"model":"qwen2.5:1.8b-q4_K_M","prompt":"hi","keep_alive":-1}'
curl http://localhost:11435/api/generate -d '{"model":"qwen2.5:1.5b-instruct","prompt":"hi","keep_alive":-1}'
docker exec <id> ollama ps
# Expected: CẢ 2 models trong danh sách "running", UNTIL: Forever
```

**TEST 4 — Toxiproxy:**
```bash
docker run -d -p 8474:8474 -p 8001:8001 ghcr.io/shopify/toxiproxy
# Tạo proxy + thêm toxic + verify declared metrics đọc được
curl -X POST http://localhost:8474/proxies \
  -d '{"name":"test","listen":"0.0.0.0:8001","upstream":"httpbin.org:80"}'
curl -X POST http://localhost:8474/proxies/test/toxics \
  -d '{"type":"latency","attributes":{"latency":100,"jitter":10}}'
curl http://localhost:8474/proxies/test/toxics
# Expected: JSON trả về có latency=100, jitter=10
```

**TEST 5 — RAM tổng:**
```bash
# Chạy đồng thời: TEST 2 + TEST 3 + Toxiproxy + Prometheus + Grafana
free -h
# Expected: used ≤ 8GB trên host 12GB
```

**Acceptance Criteria Phase 0:**
- ✅ Tất cả 5 tests PASS
- ✅ `ollama ps` trên edge-node show 2 models UNTIL: Forever
- ✅ VRAM trên cloud-node ≤ 6GB sau warmup

---

### PHASE 1 — Infrastructure Docker Compose (Tuần 2-3, tháng 5)

#### Task 1.1 — Docker Compose với đầy đủ env vars
- [ ] Viết `docker-compose.yml` với tất cả env vars từ Phần 8.1
- [ ] Viết entrypoint scripts cho cloud-node và edge-node (Phần 8.2)
- [ ] Viết `toxiproxy_init.json` với 2 proxy definitions
- [ ] Verify: `docker-compose up` → tất cả containers healthy

#### Task 1.2 — Gateway cơ bản với strategy routing
- [ ] FastAPI gateway nhận `BENCHMARK_STRATEGY` env
- [ ] PROPOSED: gọi `POST /route` từ orchestrator → forward data plane
- [ ] BASELINE-1: round-robin counter
- [ ] BASELINE-2: always forward `CLOUD_INFERENCE_URL`
- [ ] BASELINE-3: always forward `EDGE_INFERENCE_URL`
- [ ] TTFT middleware: timestamp before/after Ollama call

#### Task 1.3 — Toxiproxy setup và profile scripts
- [ ] `network/profiles/good.py`: DELETE existing toxics → POST new GOOD profile toxics
- [ ] `network/profiles/medium.py`: tương tự với MEDIUM values
- [ ] `network/profiles/bad.py`: tương tự với BAD values
- [ ] Verify: GOOD profile → latency declared = 15ms cloud, 5ms edge

#### Task 1.4 — Model warmup verification
- [ ] Sau `docker-compose up`, chạy warmup script
- [ ] Verify: `GET http://localhost:11434/api/ps` → cloud model listed "running"
- [ ] Verify: `GET http://localhost:11435/api/ps` → BOTH edge models listed "running"
- [ ] Verify: subsequent inference requests không có cold start delay

**Acceptance Criteria Phase 1:**
- ✅ `docker-compose up` → tất cả healthy
- ✅ 2 Ollama nodes nhận requests qua Toxiproxy
- ✅ Direct Ollama calls (control plane) bypass Toxiproxy, xác nhận bằng response time < 1ms
- ✅ Cả 2 edge models luôn loaded (KEEP_ALIVE=-1 hoạt động)
- ✅ 4 benchmark strategies đều hoạt động qua `BENCHMARK_STRATEGY` env

---

### PHASE 2 — CATS Telemetry & MetricsCache (Tuần 4, tháng 5 — Tuần 1, tháng 6)

#### Task 2.1 — MetricsCache module
- [ ] `metrics_cache.py`: Python dict với threading.Lock
- [ ] Async collection loops: Toxiproxy reader (5s), Ollama queue (500ms), sys stats (2s)
- [ ] Thread-safe read/write
- [ ] Unit test: concurrent reads không race condition

#### Task 2.2 — Toxiproxy reader
- [ ] Query `GET /proxies/{name}/toxics` mỗi 5s
- [ ] Parse latency, jitter, bandwidth từ JSON response
- [ ] Handle "no toxics" case → defaults
- [ ] Verify với cả GOOD/MEDIUM/BAD profiles

#### Task 2.3 — Compute metrics collection (CONTROL PLANE — bypass Toxiproxy)
- [ ] Queue depth: `GET {CLOUD_METRICS_URL}/api/ps` trực tiếp
- [ ] GPU util: `subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"])`
- [ ] CPU util: `/proc/stat` delta giữa 2 lần đọc cách nhau 2s
- [ ] TTFT: FastAPI middleware ghi vào MetricsCache sau mỗi request

#### Task 2.4 — Prometheus push (visualization only)
- [ ] Push MetricsCache values lên Prometheus Gateway mỗi 5s
- [ ] Grafana dashboard: 8 panels (latency, bandwidth, queue, gpu, cpu, ttft, rps, routing)

**Acceptance Criteria Phase 2:**
- ✅ MetricsCache cập nhật đúng interval
- ✅ Khi switch profile GOOD → BAD: declared latency tăng đúng trong < 10s
- ✅ Queue depth tăng khi gửi concurrent requests (verify với BASELINE-2 + HIGH load ngắn)
- ✅ GPU util tăng khi cloud-node đang inference
- ✅ Không có dữ liệu nào đi qua Toxiproxy trong CONTROL PLANE (verify bằng timing)

---

### PHASE 3 — Tier-2 Tactical Agent (Tuần 2, tháng 6)

#### Task 3.1 — CATS scoring với 4-term formula
- [ ] Implement `cats_score(site)` đúng formula v5.0 (không có packet_loss)
- [ ] Tag override: "fast_ok" và "high_quality"
- [ ] Handle: site unreachable → score = 0
- [ ] Unit tests: ≥ 25 scenarios bao phủ edge cases

#### Task 3.2 — OPA integration với input schema đúng
- [ ] Gọi `POST http://opa:8181/v1/data/routing/allow` với JSON schema Phần 3.6
- [ ] Parse response `{"result": {"allow": bool, "reason": str}}`
- [ ] Fallback: nếu OPA unreachable → log warning, cho phép request tiếp tục

#### Task 3.3 — Routing decision API
- [ ] `POST /route` → `{node, inference_url, model, cats_scores, reason, opa_decision}`
- [ ] Đọc từ MetricsCache (không phải Prometheus)
- [ ] Đọc current_template từ SharedState
- [ ] P99 < 10ms (không có network call trong hot path)

**Acceptance Criteria Phase 3:**
- ✅ 25/25 unit tests pass
- ✅ Decision latency P99 < 10ms (đo với 1000 consecutive calls)
- ✅ OPA rejects đúng khi inject mock overloaded metrics
- ✅ RULE 4 hoạt động: cả 2 sites bị reject → cloud vẫn phục vụ

---

### PHASE 4 — Safety Gate OPA (Tuần 2-3, tháng 6)

#### Task 4.1 — Rego policies
- [ ] Viết `routing.rego` với 5 rules theo schema Phần 3.7
- [ ] Test với `opa eval` trước khi integrate
- [ ] Verify tất cả input fields đúng tên

#### Task 4.2 — 5 violation scenarios
- [ ] RULE 1: inject queue_depth=55 → site rejected
- [ ] RULE 2: inject compute_util=95 → site rejected
- [ ] RULE 3: inject predicted_latency=600ms, SLA=500ms → rejected
- [ ] RULE 4: cả 2 sites vi phạm RULE 1 → cloud vẫn phục vụ (force fallback)
- [ ] RULE 5: tag="high_quality" + site_state="DEGRADED" + site="edge" → edge rejected

**Acceptance Criteria Phase 4:**
- ✅ 5/5 scenarios đúng
- ✅ OPA response time < 5ms (local Docker network)

---

### PHASE 5 — Tier-1 Strategic Agent (Tuần 3-4, tháng 6)

#### Task 5.1 — Telemetry aggregator
- [ ] Đọc MetricsCache → tạo summary JSON (30s window average)
- [ ] Tính current_rps và previous_rps (từ Gateway request counter)
- [ ] Summary schema khớp với Tier-1 LLM prompt

#### Task 5.2 — LLM classification
- [ ] Gọi Qwen2.5-1.5B qua `STRATEGIC_AGENT_URL` (control plane, bypass Toxiproxy)
- [ ] Timeout: 5s (STRATEGIC_TIMEOUT_S)
- [ ] Parse: strip → check in 5 valid labels → return
- [ ] Nếu invalid hoặc timeout → fallback rule-based

#### Task 5.3 — SharedState và template publishing
- [ ] Thread-safe SharedState với threading.RLock
- [ ] Tier-1 update mỗi 30s, Tier-2 đọc per-request (non-blocking)
- [ ] Initial: STATE_NORMAL template khi boot

#### Task 5.4 — Validation
- [ ] Run 60 phút liên tục, switch profile 3 lần → verify state changes
- [ ] Measure Tier-1 latency: target < 3s P95

**Acceptance Criteria Phase 5:**
- ✅ Tier-1 không crash sau 60 phút
- ✅ State change detect trong ≤ 1 epoch (30s) sau profile switch
- ✅ Fallback rule-based fire khi inject mock invalid LLM output

---

### PHASE 6 — Integration & Stability Test (Tuần 1, tháng 7)

#### Task 6.1 — Full stack smoke test
- [ ] `docker-compose up` → warmup → 50 requests mix tags → verify routing đúng
- [ ] 5/5 OPA rules verify qua integration test
- [ ] Grafana: tất cả 8 panels có data

#### Task 6.2 — Stability test (60 phút)
- [ ] Locust 10 req/s × 60 phút
- [ ] Monitor: không container crash, không memory leak
- [ ] CPU không stuck ở 100% liên tục (cpuset isolation hoạt động)
- [ ] Tier-1 classification latency average < 3s

#### Task 6.3 — Live profile switch test
- [ ] Switch GOOD → MEDIUM → BAD → GOOD trong khi running
- [ ] Tier-1 detect state change mỗi lần
- [ ] Không drop request khi switch

#### Task 6.4 — Benchmark dry run
- [ ] 1 experiment đầy đủ (PROPOSED, GOOD, LOW) → CSV đúng format
- [ ] Estimate: 24 experiments ≤ 3 giờ

**Acceptance Criteria Phase 6:**
- ✅ 60 phút không crash
- ✅ Experiment isolation procedure hoạt động (queue về 0 giữa experiments)
- ✅ CPU orchestrator không bao giờ ảnh hưởng routing latency

---

### PHASE 7 — Tier-1 Offline Evaluation (Tuần 2, tháng 7)

#### Task 7.1 — Tạo 100 labeled snapshots
- [ ] Export telemetry log từ Phase 6 stability test
- [ ] Sample ≥ 15 snapshots mỗi state (distribute đều)
- [ ] Label bằng rule-based (ground truth 100%)
- [ ] Manual verify 10 random samples

#### Task 7.2 — LLM evaluation
- [ ] Run 100 snapshots qua Qwen2.5-1.5B
- [ ] Record: output, parse_result, is_correct, latency
- [ ] Tính accuracy (%), confusion matrix (5×5)
- [ ] Tính fallback_rate (% invalid outputs)

#### Task 7.3 — Analysis và charts
- [ ] Confusion matrix heatmap (matplotlib seaborn)
- [ ] Per-state accuracy bar chart
- [ ] Document: "LLM accuracy = X%, fallback_rate = Y%"

**Acceptance Criteria Phase 7:**
- ✅ LLM accuracy ≥ 85%
- ✅ Confusion matrix có thể dùng trong thesis

---

### PHASE 8 — Benchmark 24 Experiments (Tuần 3-4, tháng 7)

#### Task 8.1 — Automation
- [ ] `run_experiment.py`: setup → Locust → collect CSV → experiment isolation
- [ ] `run_all.py`: loop 24 combinations với isolation giữa experiments

#### Task 8.2 — Chạy benchmark
- [ ] Dry run 3 experiments đầu → verify CSV
- [ ] Chạy 24 experiments (~3 giờ tổng)

#### Task 8.3 — ROUGE-L collection
- [ ] Chạy 100 prompts qua `/quality-sample` (MEDIUM profile, LOW load)
- [ ] Tính ROUGE-L với `rouge-score` library

**Acceptance Criteria Phase 8:**
- ✅ 24/24 experiments hoàn thành
- ✅ PROPOSED SLA violation rate < baselines trong ≥ 2/3 profiles
- ✅ ROUGE-L scored cho 100 pairs

---

### PHASE 9 — Analysis & Visualization (Tuần 1, tháng 8)

- [ ] Plot P50/P95/P99 latency (grouped bar, 4 strategies × 3 profiles)
- [ ] Plot SLA violation rate heatmap
- [ ] Plot CDF latency: PROPOSED vs BASELINE-2 vs BASELINE-3
- [ ] Plot ROUGE-L: quality trade-off
- [ ] Plot routing distribution timeline
- [ ] Plot Tier-1 state distribution pie chart
- [ ] Export LaTeX tables
- [ ] Tất cả charts: 300 DPI PNG

**Acceptance Criteria Phase 9:**
- ✅ ≥ 8 production-quality charts

---

### PHASE 10 — Báo cáo (Tuần 2-4, tháng 8)

**6 Chapters:**

**Chapter 1 — Giới thiệu:** Bối cảnh, vấn đề, research gap (LLM routing không CATS-aware), contributions, outline.

**Chapter 2 — Related Work:** CATS IETF framework, LLM inference tại edge, LLM routing landscape (RouteLLM vs CATS approach), Agentic AI patterns, paper 2602.07215 (so sánh).

**Chapter 3 — Thiết kế hệ thống:** Kiến trúc, Agentic PRA framing, CATS metric schema (v5.0, 8 metrics), CATS formula (4-term), Safety gate, Toxiproxy emulation methodology.

**Chapter 4 — Implement:** Environment, Docker Compose config, MetricsCache design (tại sao không dùng Prometheus cho routing), Data plane vs Control plane separation.

**Chapter 5 — Evaluation:** Setup (24 experiments), Tier-1 evaluation (100 snapshots), Latency results, SLA analysis, ROUGE-L quality, Routing overhead.

**Chapter 6 — Kết luận:**
- Summary contributions
- Key findings
- **Limitations** (bắt buộc, tăng điểm học thuật):
  - Single-host simulation (không phải physical distributed)
  - Declared metrics thay vì active probing (Toxiproxy limitation)
  - Toxiproxy không hỗ trợ packet-level loss simulation
  - OLLAMA_NUM_PARALLEL=2 → throughput cap thấp hơn production
  - CATS weights hardcoded, chưa adaptive
- **IF/ELSE defense** (viết rõ trong Chapter 6):
  *"The current metric schema is structured enough for a deterministic classifier to achieve 100% accuracy. The LLM-based Tier-1 agent is validated as an architectural proof-of-concept with measured X% accuracy, demonstrating viability for future extensions to unstructured telemetry signals such as free-text log messages. The overhead cost (≈2-3s per 30s epoch) is justified by the extensibility gained."*
- Future work: multi-host, adaptive weights, larger model pool, real packet loss simulation (tc/netem on bare metal)

---

## PHẦN 11 — CONFIGURATION (.env v5.0 FINAL)

```env
# === NODES — DATA PLANE (qua Toxiproxy) ===
CLOUD_INFERENCE_URL=http://toxiproxy:8001
EDGE_INFERENCE_URL=http://toxiproxy:8002

# === NODES — CONTROL PLANE (bypass Toxiproxy) ===
CLOUD_METRICS_URL=http://cloud-node:11434
EDGE_METRICS_URL=http://edge-node:11435
STRATEGIC_AGENT_URL=http://edge-node:11435

# === MODELS ===
CLOUD_MODEL=qwen2.5:7b-q4_K_M
EDGE_INFERENCE_MODEL=qwen2.5:1.8b-q4_K_M
STRATEGIC_AGENT_MODEL=qwen2.5:1.5b-instruct

# === TOXIPROXY ===
TOXIPROXY_API=http://toxiproxy:8474
CLOUD_PROXY_NAME=cloud-proxy
EDGE_PROXY_NAME=edge-proxy

# === BENCHMARK ===
BENCHMARK_STRATEGY=PROPOSED    # PROPOSED|BASELINE-1|BASELINE-2|BASELINE-3

# === SLA ===
SLA_TARGET_MS=500

# === CATS SCORING (v5.0 — không có W_RTT, thay bằng W_LATENCY) ===
W_LATENCY=0.30
W_QUEUE=0.30
W_COMPUTE=0.25
W_QUALITY=0.15
W_QUALITY_FAST=0.05
W_QUALITY_HQ=0.30

# === MODEL QUALITY ===
QUALITY_CLOUD=1.0
QUALITY_EDGE=0.6

# === THRESHOLDS ===
MAX_QUEUE_DEPTH=50
MAX_GPU_UTIL_PCT=90
MAX_CPU_UTIL_PCT=92
LOW_BANDWIDTH_KBPS=1000

# === TIER-1 THRESHOLDS ===
STATE_EDGE_LOADED_QUEUE=35
STATE_EDGE_LOADED_CPU=85
STATE_DEGRADED_LATENCY_MS=150
STATE_DEGRADED_BANDWIDTH_KBPS=1000
STATE_BURST_RATIO=1.5

# === TIER-1 TIMING ===
STRATEGIC_EPOCH_S=30
STRATEGIC_TIMEOUT_S=5
STRATEGIC_MAX_RETRIES=3

# === COLLECTION INTERVALS ===
TOXIPROXY_READER_INTERVAL_S=5
OLLAMA_QUEUE_INTERVAL_S=0.5
COMPUTE_METRICS_INTERVAL_S=2
PROMETHEUS_PUSH_INTERVAL_S=5
```

---

## PHẦN 12 — ĐIỀU KIỆN HOÀN THÀNH (v5.0)

| # | Tiêu chí | Target |
|---|---|---|
| 1 | Phase 0: 5/5 Go/No-Go tests pass | ✅ |
| 2 | Phase 0: 2 edge models ALWAYS loaded (UNTIL: Forever) | ✅ |
| 3 | Phase 1: Data plane / Control plane routing tách biệt và verified | ✅ |
| 4 | Phase 2: 8 CATS metrics đúng (5 passive + 3 declared, không có packet_loss) | ✅ |
| 5 | Phase 3: Routing P99 < 10ms từ MetricsCache (không phải Prometheus) | ✅ |
| 6 | Phase 4: OPA 5/5 rules enforce đúng với correct input schema | ✅ |
| 7 | Phase 5: Tier-1 < 3s P95, không crash 60 phút | ✅ |
| 8 | Phase 6: 60 phút stability, CPU orchestrator không gây routing delay | ✅ |
| 9 | Phase 7: LLM accuracy ≥ 85% trên 100 snapshots | ✅ |
| 10 | Phase 8: 24/24 experiments, PROPOSED < baselines trong ≥ 2/3 profiles | ✅ |
| 11 | Phase 8: ROUGE-L computed cho 100 pairs | ✅ |
| 12 | Phase 9: ≥ 8 production charts | ✅ |
| 13 | Phase 10: 6 chapters + Limitations section đầy đủ + IF/ELSE defense | ✅ |

---

## PHẦN 13 — TIMELINE

```
Tháng 5, Tuần 1:     Phase 0  — Môi trường (1 tuần)
Tháng 5, Tuần 2-3:   Phase 1  — Infrastructure (2 tuần)
Tháng 5-6, Tuần 4-1: Phase 2  — CATS Telemetry (2 tuần)
Tháng 6, Tuần 2:     Phase 3  — Tier-2 (1 tuần)
Tháng 6, Tuần 2-3:   Phase 4  — OPA (1 tuần)
Tháng 6, Tuần 3-4:   Phase 5  — Tier-1 (2 tuần)
Tháng 7, Tuần 1:     Phase 6  — Integration (1 tuần)
Tháng 7, Tuần 2:     Phase 7  — Tier-1 Eval (1 tuần)
Tháng 7, Tuần 3-4:   Phase 8  — Benchmark (2 tuần)
Tháng 8, Tuần 1:     Phase 9  — Analysis (1 tuần)
Tháng 8, Tuần 2-4:   Phase 10 — Report (3 tuần)
────────────────────────────────────────────────
TỔNG: 17 tuần   DEADLINE: cuối tháng 8/2026
```

---

*v5.0 FINAL — Tháng 5/2026*
*Tất cả 15 lỗi đã được xác định và xử lý.*
*Kiến trúc ổn định. Không thay đổi thêm nếu không có lý do kỹ thuật rõ ràng.*
