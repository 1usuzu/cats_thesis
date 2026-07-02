# CATS Thesis - Context-Aware Traffic Steering

CATS (Context-Aware Traffic Steering) là hệ thống routing inference LLM giữa Cloud và Edge sử dụng AI-assisted routing (Tier-1: Strategic Agent, Tier-2: Tactical Agent) kết hợp với các cơ chế ràng buộc an toàn bằng OPA (Open Policy Agent).

## Hướng dẫn chạy (Quick Start)

### Yêu cầu
- Docker và Docker Compose.
- Python 3.10+ (cho việc phát triển và chạy test cục bộ).
- GPU NVIDIA (cho cloud node) nếu có hỗ trợ.

### Cài đặt
1. Clone repository về máy.
2. Thiết lập môi trường ảo và cài đặt thư viện:
   ```bash
   make setup
   ```
3. Chạy hệ thống bằng Docker Compose:
   ```bash
   make docker-up
   ```

### Các dịch vụ chính
- **Gateway**: `http://localhost:8000`
- **Orchestrator**: `http://localhost:8080`
- **Cloud Node (Ollama)**: `http://localhost:11434`
- **Edge Node (Ollama)**: `http://localhost:11435`
- **Grafana**: `http://localhost:3000`
- **Prometheus**: `http://localhost:9090`

## Known Bugs & Pending Issues (Theo CATS_NEXT_STEPS_AGENT_BRIEF & ROADMAP 2.2)
Hiện tại dự án đang trong giai đoạn Research Prototype và có một số vấn đề runtime/logic cần sửa trước khi chạy Benchmark 24-run:

1. **Toxiproxy Init**: `docker-compose.yml` không tự động tạo `cloud-proxy` và `edge-proxy`.
2. **OPA Rule 5 State Mismatch**: Code gửi `STATE_DEGRADED` nhưng Rego lại check `DEGRADED`, khiến Rule 5 không bao giờ được trigger.
3. **OPA Hot Path Timeout**: Việc tạo `httpx.AsyncClient` liên tục trong hot path làm chậm hệ thống, đồng thời lỗi fail-open trả về True gây nhầm lẫn bypass với allow.
4. **Predicted Latency Semantics**: `predicted_latency_ms` chỉ mới tính network latency của Toxiproxy thay vì E2E latency.
5. **Queue Metric Semantics**: Metric hiện tại đo đếm `gateway_inflight` nhưng document ghi là queue depth nội bộ của Ollama.
6. **Compute Signals Limitations**: Đoán nhận GPU/CPU thông qua `nvidia-smi` và `/proc/stat` từ Orchestrator không phản ánh đúng trạng thái của Cloud/Edge Node.
7. **Prometheus Scrape Mismatch**: Cố gắng scrape `gateway:8000/metrics` nhưng Gateway chưa expose `/metrics`.
8. **CATS Scoring Tests**: Unit tests vẫn đang sử dụng weights cũ (cần update W_LATENCY=0.3, v.v.).
9. **Benchmark Automation**: Cần xử lý cô lập các lần chạy (experiment isolation) và file dataset phải trỏ tới ShareGPT-500.

---
*Lưu ý: Các bug trên đã được ghi chú lại theo đúng chuẩn mực tài liệu ROADMAP và CHƯA ĐƯỢC SỬA nhằm đảm bảo tính toàn vẹn của giai đoạn review này.*
