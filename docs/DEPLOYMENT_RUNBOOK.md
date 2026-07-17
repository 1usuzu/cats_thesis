# CATS — Deployment Runbook (Ngày bảo vệ)

Checklist triển khai cho buổi bảo vệ luận văn. Thực hiện **ít nhất 1 ngày trước** buổi bảo vệ.

---

## 1. Pre-pull Images & Models

### 1.1 Pull Docker images

```bash
# Pull tất cả images (cần mạng Internet)
make docker-pre-pull

# Hoặc:
docker compose pull
```

Danh sách images sẽ được pull (đã ghim version):

| Image | Version | Size ước tính |
|-------|---------|--------------|
| `ollama/ollama` | `0.31.2` | ~3.2 GB |
| `ghcr.io/shopify/toxiproxy` | `2.12.0` | ~20 MB |
| `openpolicyagent/opa` | `1.18.2` | ~30 MB |
| `prom/prometheus` | `v3.13.0` | ~110 MB |
| `grafana/grafana` | `13.1.0` | ~400 MB |
| + các build images (gateway, orchestrator, web, toxiproxy-init) | local build | ~500 MB tổng |

### 1.2 Pull & warm-up models

Chạy hệ thống 1 lần đầy đủ để tải models vào volumes:

```bash
# Chạy bản GPU (cho máy demo)
make docker-up

# Theo dõi tiến trình pull model:
docker compose logs -f cloud-node edge-node
```

Đợi đến khi thấy:
- `Cloud-node ready.` trong log cloud-node
- `Edge-node ready (both models loaded).` trong log edge-node

Models sẽ được lưu trong Docker volumes (`cloud-models`, `edge-models`) và tự động reuse cho các lần chạy sau.

**Thời gian ước tính (lần đầu):**
- Cloud model `qwen2.5:7b`: ~4.7 GB, ~5-15 phút
- Edge models `qwen2.5:1.5b` + `qwen2.5:1.5b-instruct`: ~2 GB, ~3-10 phút

### 1.3 Xác nhận images đã cached

```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | Select-String "ollama|toxiproxy|opa|prometheus|grafana"
```

Phải thấy đủ 5 images với đúng version tag.

---

## 2. Test chạy Offline (Rút mạng)

Mục đích: đảm bảo hệ thống hoạt động **không cần Internet** trong buổi bảo vệ.

### 2.1 Quy trình test

```bash
# 1. Dừng hệ thống (nếu đang chạy)
make docker-down

# 2. NGẮT KẾT NỐI MẠNG (rút cáp / tắt WiFi)

# 3. Chạy lại hệ thống
make docker-up

# 4. Đợi healthcheck (xem mục 3 bên dưới)

# 5. Kiểm tra nhanh:
#    - Mở http://localhost:3001 (Web UI)
#    - Mở http://localhost:3000 (Grafana, user: admin, pass: admin)
#    - Gửi 1 request test qua Web UI hoặc:
curl -X POST http://localhost:8000/v1/chat -H "Content-Type: application/json" -d '{"prompt": "hello", "request_tag": "default"}'

# 6. KẾT NỐI LẠI MẠNG
```

### 2.2 Checklist xác nhận offline

- [ ] Tất cả containers khởi động thành công (không pull image)
- [ ] Models load từ volume (không tải lại từ Internet)
- [ ] Web UI hiển thị đúng tại `http://localhost:3001`
- [ ] Gateway trả response cho request test
- [ ] Grafana dashboard accessible tại `http://localhost:3000`

---

## 3. Trình tự khởi động + Healthcheck

### 3.1 Thứ tự service startup (tự động qua depends_on)

```
1. cloud-node, edge-node, toxiproxy, opa, prometheus
   ↓ (cloud/edge: pull + warmup model, ~2-5 phút nếu đã cache)
2. toxiproxy-init (tạo proxy, chờ toxiproxy started)
   ↓
3. orchestrator (chờ toxiproxy-init completed + opa started)
   ↓
4. gateway (chờ orchestrator healthy)
   ↓
5. web (chờ gateway + orchestrator healthy)
6. grafana (chờ prometheus healthy)
```

### 3.2 Kiểm tra healthcheck

```bash
# Xem trạng thái tất cả services:
docker compose ps

# Đợi tất cả healthy (script kiểm tra):
# Chạy lặp cho đến khi không còn service nào "starting" hay "unhealthy":
docker compose ps --format json | Select-String -Pattern '"Health":"healthy"'
```

**Thời gian khởi động ước tính:**
- Nếu models đã cache trong volume: **2-5 phút** (chủ yếu chờ warmup load model vào VRAM/RAM)
- Nếu phải pull models lần đầu: **15-30 phút**

### 3.3 Xác minh GPU thực sự được sử dụng (chỉ bản GPU)

> ⚠️ **Bước quan trọng:** Sau khi chạy `make docker-up`, phải verify cloud-node đang dùng GPU — không chỉ dựa vào container "healthy".

```bash
# Cách 1: Kiểm tra nvidia-smi trong container cloud-node
docker exec cats_thesis-cloud-node-1 nvidia-smi

# Expected output: bảng GPU info (tên GPU, memory usage, processes)
# Nếu thấy "command not found" hoặc "Failed to initialize NVML" → ĐANG CHẠY CPU!

# Cách 2: Kiểm tra log Ollama
docker compose logs cloud-node 2>&1 | Select-String -Pattern "CUDA|GPU|NVIDIA|cpu"

# Expected: dòng log chứa "CUDA" hoặc "GPU" cho thấy Ollama nhận GPU
# Nếu thấy "cpu" → đang chạy CPU mode

# Cách 3: Kiểm tra docker inspect runtime
docker inspect cats_thesis-cloud-node-1 --format '{{.HostConfig.Runtime}}'

# Expected: "nvidia"
# Nếu thấy "runc" → đang chạy CPU mode, có thể chạy nhầm lệnh
```

**Nếu phát hiện chạy CPU thay vì GPU:**
1. Dừng hệ thống: `make docker-down`
2. Kiểm tra NVIDIA Container Toolkit: `nvidia-smi` (trên host)
3. Đảm bảo dùng đúng lệnh: `make docker-up` (không phải `make docker-up-cpu`)
4. Chạy lại: `make docker-up`

### 3.4 Smoke test nhanh

```bash
# 1. Gateway health
curl -s http://localhost:8000/health

# 2. Orchestrator health
curl -s http://localhost:8080/health

# 3. Toxiproxy proxies tồn tại
curl -s http://localhost:8474/proxies | python -m json.tool

# 4. Test inference end-to-end
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "request_tag": "default"}'
```

---

## 4. Tài sản dự phòng (Backup khi demo live lỗi)

### 4.1 Screenshots/Plots đã có sẵn

Các kết quả benchmark đã lưu trong `analysis/plots/`:

| File | Nội dung |
|------|----------|
| `analysis/plots/routing_distribution.png` | Phân bổ routing giữa Cloud/Edge theo chiến lược |
| `analysis/plots/sla_violations.png` | Tỉ lệ lỗi và SLA violations so sánh giữa các strategies |
| `analysis/plots/latency_comparison.png` | So sánh P99 latency giữa các strategies |

### 4.2 Chuẩn bị trước buổi bảo vệ

- [ ] **Copy plots ra USB/Google Drive** — đề phòng máy demo không mở được file
- [ ] **Chụp screenshot Web UI đang chạy** — mở `http://localhost:3001`, chụp giao diện, lưu ra ngoài project
- [ ] **Chụp screenshot Grafana dashboard** — mở `http://localhost:3000`, chụp dashboard, lưu ra ngoài project
- [ ] **Quay video demo ngắn (30-60 giây)** — gửi 1-2 request qua Web UI, cho thấy routing decision, lưu file video

### 4.3 Kịch bản dự phòng khi demo live lỗi

| Lỗi | Phương án |
|-----|-----------|
| Máy GPU không khởi động được Docker | Chuyển sang CPU-only: `make docker-up-cpu`. Cảnh báo hội đồng inference sẽ chậm hơn. |
| Container crash/restart liên tục | Dùng screenshots/video đã chuẩn bị. Mở slides, trình bày kết quả từ plots. |
| Web UI không load | Truy cập trực tiếp API: `curl http://localhost:8000/v1/chat ...` từ terminal. |
| Grafana không hiển thị data | Mở screenshots Grafana đã chụp trước. |
| Không có mạng + models chưa cache | Dùng plots + video demo đã quay sẵn. **Đây là lý do phải test offline (mục 2) trước.** |

### 4.4 Checklist cuối cùng (ngày bảo vệ, trước khi vào phòng)

- [ ] Máy demo đã bật, Docker đã chạy
- [ ] `make docker-up` đã chạy xong, tất cả services healthy
- [ ] GPU đã verify (mục 3.3)
- [ ] Web UI mở sẵn trong browser tab
- [ ] Grafana mở sẵn trong browser tab khác
- [ ] USB/Drive chứa plots + video dự phòng đã cắm/mở sẵn
- [ ] Terminal mở sẵn ở project directory (đề phòng cần chạy lệnh)
