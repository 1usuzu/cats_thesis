# CATS Thesis - Context-Aware Traffic Steering

CATS (Context-Aware Traffic Steering) là hệ thống routing inference LLM giữa Cloud và Edge sử dụng AI-assisted routing (Tier-1: Strategic Agent, Tier-2: Tactical Agent) kết hợp với các cơ chế ràng buộc an toàn bằng OPA (Open Policy Agent).

## Hướng dẫn chạy (Quick Start)

> ⚠️ **Lưu ý quan trọng:** Mặc định `docker compose up` (không kèm `-f`) chạy ở chế độ **CPU-only**, không sử dụng GPU. Để chạy với GPU NVIDIA (demo/bảo vệ), dùng `make docker-up` hoặc xem mục [Chế độ GPU / CPU-only](#chế-độ-gpu--cpu-only) bên dưới.

### Yêu cầu
- Docker và Docker Compose v2 (`docker compose` CLI plugin).
- Python 3.10+ (cho việc phát triển và chạy test cục bộ).
- Node.js 20+ (để dev Web UI).
- GPU NVIDIA + NVIDIA Container Toolkit (cho chế độ GPU — xem bên dưới).

### Cài đặt

1. Clone repository về máy.

2. Tạo file cấu hình môi trường:
   ```bash
   cp .env.example .env
   ```
   > File `.env.example` chứa tất cả giá trị mặc định. Chỉ cần sửa `CATS_API_KEYS` và `CATS_API_KEY` nếu muốn bật xác thực.

3. Thiết lập môi trường ảo và cài đặt thư viện (cho phát triển cục bộ):
   ```bash
   make setup
   ```

4. Chạy hệ thống bằng Docker Compose:
   ```bash
   make docker-up        # GPU (mặc định cho demo/bảo vệ)
   make docker-up-cpu    # CPU-only (không cần GPU NVIDIA)
   ```

> ⚠️ **Dung lượng và thời gian tải model lần đầu:**
> Lần chạy đầu tiên, hệ thống sẽ tự động tải các model LLM vào Docker volumes:
> - `qwen2.5:7b` (~4.7 GB) cho cloud-node
> - `qwen2.5:1.5b` (~1 GB) + `qwen2.5:1.5b-instruct` (~1 GB) cho edge-node
>
> **Tổng cộng ~7 GB**, mất khoảng **10–30 phút** tùy tốc độ mạng. Các lần chạy sau sẽ dùng cache từ volume, không cần tải lại.

### Chế độ GPU / CPU-only

| Chế độ | Lệnh | Mô tả |
|--------|-------|-------|
| **GPU** (khuyên dùng cho demo) | `make docker-up` | Dùng `docker-compose.gpu.yml` override, cloud-node chạy trên NVIDIA GPU |
| **CPU-only** | `make docker-up-cpu` | Chỉ dùng `docker-compose.yml` base, không yêu cầu GPU NVIDIA |

**Chế độ CPU-only:**
- Không cần GPU NVIDIA hay NVIDIA Container Toolkit.
- Cloud-node sẽ chạy inference trên CPU — **chậm hơn đáng kể** (ước tính 10–100x so với GPU, tùy model và phần cứng).
- Model mặc định vẫn là `qwen2.5:7b`. Có thể đổi sang model nhẹ hơn bằng biến `CLOUD_MODEL` trong `.env` (ví dụ `qwen2.5:1.5b`) — lưu ý đây là trade-off: giảm thời gian suy luận nhưng giảm chất lượng output, và **kết quả sẽ khác với benchmark GPU đã công bố**.

**Lệnh trực tiếp (không dùng Makefile):**
```bash
# GPU:
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# CPU-only:
docker compose up -d
```

### Các dịch vụ chính
- **Web UI**: `http://localhost:3001` (Giao diện chính)
- **Gateway**: `http://localhost:8000`
- **Orchestrator**: `http://localhost:8080`
- **Cloud Node (Ollama)**: `http://localhost:11434`
- **Edge Node (Ollama)**: `http://localhost:11435`
- **Grafana**: `http://localhost:3000`
- **Prometheus**: `http://localhost:9090`
- **Ngrok Tunnel Dashboard**: `http://localhost:4040` (Quản lý kết nối Internet)

### Truy cập từ Điện thoại / Mạng ngoài (Internet Tunneling)

Hệ thống cung cấp sẵn công cụ Ngrok để tạo đường hầm an toàn kết nối thẳng từ Internet vào máy tính của bạn, giúp bạn có thể mở Web UI trên điện thoại (qua 4G) hoặc gửi link cho bạn bè/giáo viên hướng dẫn.

**Cách 1: Dùng mạng LAN (WiFi)**
Nếu điện thoại và máy tính bắt cùng 1 cục WiFi, bạn không cần cài thêm gì. Chỉ cần tìm địa chỉ IP của máy tính (ví dụ: `192.168.1.15`) và mở trình duyệt trên điện thoại: `http://192.168.1.15:3001`

**Cách 2: Dùng Domain Internet (Ngrok)**
Để có một link `.com` hoặc `.app` truy cập từ bất cứ đâu:
1. Đăng ký tài khoản miễn phí tại [ngrok.com](https://ngrok.com).
2. Vào phần "Your Authtoken" để lấy chuỗi token.
3. Mở file `.env` trong thư mục dự án, tìm đến dòng `NGROK_AUTHTOKEN=` và dán token của bạn vào:
   ```env
   NGROK_AUTHTOKEN=1234567890abcdef_abcdef1234567890
   ```
4. Khởi động lại hệ thống: `make docker-down` rồi `make docker-up`.
5. Mở Dashboard của Ngrok tại `http://localhost:4040/status` để lấy đường link Public URL (dạng `https://xyz.ngrok-free.app`). Truy cập link này trên điện thoại/4G để sử dụng!

## Kết quả Benchmark & Đánh giá (CATS Final Results)

Hệ thống đã trải qua quá trình review và fix toàn bộ các vấn đề (Bugs/Pending Issues) theo `AGENTIC_ROADMAP 2.2`. 
Hiện tại, Benchmark 24-run đã chạy thành công 100% với tính năng tự động cô lập (isolate network profiles) và thu thập custom metrics bằng Locust.

### 1. Phân bổ định tuyến (Routing Distribution)
Chiến lược **PROPOSED** tự động dồn request xuống Edge hoặc kích hoạt Fallback khi chất lượng Cloud (latency, inflight queue) chuyển biến xấu.
![Routing Distribution](analysis/plots/routing_distribution.png)

### 2. Tỉ lệ lỗi và SLA Violations
So với các chiến lược Baseline (Cloud-only, Edge-only, Round-robin), chiến lược **PROPOSED** giúp kiểm soát và duy trì tỉ lệ lỗi (Failure Rate & SLA Miss) ở mức thấp nhất khi mạng gặp sự cố (Profile: Bad/Medium). Hiện tượng 100% failure ở các test `Low Load` đầu tiên đã chứng minh cơ chế **Circuit Breaker** hoạt động chớp nhoáng (ngắt mạch trong 20ms) để bảo vệ Gateway khỏi Ollama Cold Start.
![SLA Violations](analysis/plots/sla_violations.png)

### 3. So sánh độ trễ (P99 Latency Comparison)
![Latency Comparison](analysis/plots/latency_comparison.png)

## Known Limitations

Đây là research-grade prototype, không phải production system. Các hạn chế đã biết (đối chiếu từ [CATS_NEXT_STEPS_AGENT_BRIEF.md](docs/CATS_NEXT_STEPS_AGENT_BRIEF.md)):

| # | Hạn chế | Mô tả | Tham chiếu |
|---|---------|-------|------------|
| 1 | **`predicted_latency_ms` chưa tính inference time** | Giá trị hiện tại chỉ phản ánh network latency từ Toxiproxy, chưa bao gồm thời gian suy luận thực tế của model. OPA Rule 3 (SLA check) có thể không phản ánh chính xác end-to-end latency. | Phase 1.4 |
| 2 | **Queue metric là proxy** | Metric queue depth dùng `gateway_inflight` (số request đang xử lý tại gateway) làm proxy, không phải Ollama internal queue depth thực sự. | Phase 1.5 |
| 3 | **Compute metrics đo gián tiếp** | `nvidia-smi` được gọi từ container orchestrator (có thể không có GPU access). `/proc/stat` đo CPU của container orchestrator, không phải edge-node. Các giá trị này là tín hiệu gần đúng (proxy signals). | Phase 1.6 |
| 4 | **OPA fail-open** | Khi OPA timeout hoặc lỗi, hệ thống bypass (cho phép request đi qua) thay vì reject. Trạng thái bypass không phân biệt được với allow bình thường trong response hiện tại. | Phase 1.3 |
| 5 | **CPU inference chậm** | Chế độ CPU-only chạy inference chậm hơn đáng kể so với GPU. Kết quả benchmark đã công bố được thu thập trên GPU. | — |

---
*Dự án là research prototype phục vụ khóa luận tốt nghiệp. Xem [DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md) cho hướng dẫn triển khai ngày bảo vệ.*
