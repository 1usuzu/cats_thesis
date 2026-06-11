## 🧠 Brainstorm: Kiến trúc Hệ thống CATS (Codebase Walkthrough)

### Context
**Hệ thống CATS (Context-Aware Tiered System)** là một giải pháp định tuyến LLM thông minh (Cloud-Edge LLM Routing). Nhiệm vụ của nó là cân bằng giữa hai bài toán hóc búa: **Chi phí/Trễ mạng (Cloud)** và **Sức mạnh tính toán/Bộ nhớ (Edge)**, đảm bảo người dùng luôn nhận được câu trả lời nhanh nhất với chất lượng tốt nhất trong mọi hoàn cảnh mạng lưới.

---

### 1️⃣ The Lifecycle of a Request (Từ Giao diện đến Phản hồi)
*Chuyện gì xảy ra khi user gõ "Hello" và bấm Enter trên Dashboard?*

1. **Giao diện (Streamlit UI):** File `ui/dashboard.py` đóng gói câu prompt và `request_tag` (vd: `high_quality` hoặc `fast_ok`), gửi một POST request đến Endpoint `/v1/chat` của Gateway.
2. **Gateway (Người gác cổng):** Tại `gateway/main.py`, Gateway nhận request. Nếu chiến lược đang là `PROPOSED`, nó sẽ "tạm giữ" request lại và gọi điện cho ngài **Orchestrator** (Endpoint `/route`) để xin chỉ thị phân luồng.
3. **Orchestrator (Bộ não trung tâm):** Orchestrator chạy qua thuật toán tính điểm và hàng rào bảo vệ OPA (sẽ nói chi tiết ở phần 2), chốt lại quyết định là gửi lên `cloud` hay `edge`.
4. **Proxy & Emulation:** Gateway nhận được lệnh, lập tức forward (proxy) request HTTP đến địa chỉ của Node tương ứng. **LƯU Ý:** Nó không gửi thẳng cho Ollama, mà gửi qua **Toxiproxy** (`http://toxiproxy:8001` hoặc `8002`). Toxiproxy ở đây đóng vai trò như một "ống nước có thể bóp nghẹt", giả lập độ trễ mạng y như ngoài đời thực.
5. **Inference (Xử lý LLM):** Container `cloud-node` (Qwen 7B) hoặc `edge-node` (Qwen 1.5B) nhận request, suy luận, và stream kết quả về qua Toxiproxy, qua Gateway, rồi hiển thị lên màn hình Streamlit cho người dùng cùng với cái badge thời gian (Latency metrics).

✅ **Điểm nhấn cho luận văn:** Bạn đã tách biệt hoàn toàn **Control Plane** (Gateway, Orchestrator xin chỉ thị) và **Data Plane** (Dữ liệu prompt/text đi qua Toxiproxy và Ollama). Orchestrator không hề đọc nội dung chat, nó chỉ quan tâm đến siêu dữ liệu (metadata), đảm bảo tính bảo mật (privacy-preserving).

---

### 2️⃣ Gateway & OPA Magic (Trái tim của PROPOSED Strategy)
*Làm sao hệ thống biết nên chọn Cloud hay Edge?*

Khi Gateway gọi `/route`, bên trong `orchestrator/app.py` và `tactical_agent.py` diễn ra 2 bước cực kỳ tinh vi:

* **Bước 1: Tính điểm (Tactical Scoring):** Hệ thống lấy Metrics (từ bộ nhớ RAM) ra để tính `cats_score` cho cả Cloud và Edge. Công thức là sự kết hợp của: `Điểm Độ trễ` + `Điểm Hàng đợi (Inflight)` + `Điểm CPU/GPU` + `Trọng số Chất lượng`. Nó giống như việc chấm điểm thi đại học, ai cao hơn thì ưu tiên (`preferred_site`).
* **Bước 2: Bộ lọc An toàn OPA (Open Policy Agent):** Dù Edge có điểm cao, nhưng nếu nó đang bị quá tải (CPU > 90%), thì sao? Orchestrator lập tức gọi sang `opa/policy.rego` (Engine quy tắc kinh doanh viết bằng ngôn ngữ Rego). 
   - OPA sẽ quét các luật: *SLA có bị vi phạm không? Queue có quá dài không? Tình trạng hệ thống (Master Plan) đang là gì?*
   - Nếu OPA phán `deny` (từ chối), Orchestrator sẽ lập tức thử hỏi OPA xem trang web dự phòng (`backup_site`) có an toàn không. 
   - Nếu cả 2 đều sụp (Mạng nát, tải quá cao), hệ thống kích hoạt **`FORCE_CLOUD_FALLBACK`** - ép đẩy hết lên Cloud vì Cloud dẫu sao cũng chịu tải tốt hơn thiết bị Edge bé nhỏ.

✅ **Điểm nhấn cho luận văn:** Việc dùng OPA cho phép bạn thay đổi luật (Safety limits, SLA targets) ngay trong lúc hệ thống đang chạy bằng cách sửa file `rego` mà không cần compile lại toàn bộ code Python. Đây là tiêu chuẩn Enterprise.

---

### 3️⃣ The Benchmark Engine (Bộ Giả lập Khắc nghiệt)
*Làm sao để chứng minh thuật toán của bạn hoạt động trên "thế giới thực"?*

Thay vì "bốc phét" ra các con số, bạn đã xây dựng hẳn một buồng thử nghiệm tự động:
1. **Isolation & Trạng thái (`benchmark/isolation.py`):** Trước khi chạy mỗi kịch bản, file này sẽ clear hàng đợi, xoá trạng thái rác, và gọi API thay đổi chiến lược Gateway (PROPOSED, BASELINE 1-2-3). Nó còn bắn các prompt "Warm-up" để đảm bảo mô hình LLM đã được load sẵn lên GPU/RAM, tránh việc cold-start làm nhiễu kết quả.
2. **Network Profiles (`network/profiles/`):** Nó sử dụng Toxiproxy REST API để tiêm "độc" (Toxics) vào đường truyền TCP. 
   - Mạng **GOOD**: Trễ 20ms.
   - Mạng **BAD**: Trễ 350ms, Jitter (độ giật) 60ms, bóp băng thông.
3. **Locust Traffic Generator (`benchmark/locustfile.py`):** Đóng vai hàng chục người dùng (Users) liên tục xả request vào Gateway (Load = HIGH hoặc LOW). Cuối cùng, `generate_plots.py` gom file CSV lại để vẽ ra các biểu đồ P99 Latency và SLA bạn vừa xem.

✅ **Điểm nhấn cho luận văn:** Khả năng **Reproducibility** (Khả năng tái lập). Bất kỳ giáo sư nào clone mã nguồn của bạn về, chạy lệnh `python run_all.py` đều sẽ ra kết quả tương tự nhờ sự nhất quán của Toxiproxy và Docker Compose.

---

### 4️⃣ Key Technical Decisions (Vũ khí phòng thủ luận văn)
Dưới đây là 3 quyết định kỹ thuật "ăn tiền" nhất mà bạn có thể tự hào trình bày trước hội đồng:

1. **Kiến trúc Two-Tier Agentic Orchestration (Mô hình 2 Tầng):**
   - Không dùng 1 vòng lặp rập khuôn. Tầng 1 (**Strategic Agent**) chạy ngầm 10s/lần, nhìn bức tranh toàn cảnh để ra "Master Plan" (Ví dụ: Chuyển sang `STATE_BURST`). Tầng 2 (**Tactical Agent**) chạy mỗi khi có request, phản ứng trong vài mili-giây dựa trên khuôn mẫu của Tầng 1. Nó giống như Tướng quân vạch chiến lược, còn Lính tráng thực thi trên chiến trường.
2. **Stateless Metrics Cache phi đồng bộ (In-Memory Caching):**
   - Làm sao Orchestrator tính toán nhanh thế? Bí quyết nằm ở `metrics_cache.py`. Thay vì mỗi lần request đến lại chạy đi query Prometheus (rất chậm), hệ thống có các Background Workers (`compute_reader`, `toxiproxy_reader`) liên tục crawl dữ liệu và lưu vào biến RAM nội bộ. Khi cần định tuyến, hệ thống chỉ mất `O(1)` (gần như 0ms) để lấy dữ liệu tính toán.
3. **Fail-Open Mechanism (Cơ chế Không sập):**
   - Trong `tactical_agent.py`, nếu OPA server bị chết (Timeout), Orchestrator không báo lỗi 500 cho user. Nó bắt Exception, ghi log *"OPA connection error, BYPASSING safety gate"*, và tự động chuyển status sang `bypassed` để request vẫn được đi tiếp. Trong các hệ thống phân tán, nguyên lý "Thà phân luồng ngu còn hơn là làm sập dịch vụ của user" là một nguyên lý thiết kế tối thượng.

---

## 💡 Recommendation
Khi bảo vệ luận văn, **hãy bắt đầu bằng Demo giao diện (Streamlit)** để hội đồng thấy tính ứng dụng. Sau đó, **chuyển ngay sang trình bày cái Benchmark Engine** để chứng minh bạn đã đo lường một cách khoa học (Scientific Evaluation). Cuối cùng mới **mổ xẻ phần Gateway & OPA** để khoe hàm lượng kỹ thuật. 