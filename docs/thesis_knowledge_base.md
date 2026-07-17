# Cẩm Nang Bảo Vệ Luận Văn: Hệ Thống CATS

Tài liệu này tổng hợp toàn bộ kiến thức cốt lõi, kiến trúc hệ thống, và các "vũ khí phòng thủ" để bạn trả lời câu hỏi phản biện của hội đồng trong buổi bảo vệ luận văn.

---

## 1. Bản Chất Của CATS (Context-Aware Tiered System)
**CATS là gì?** 
Là hệ thống định tuyến (Routing) thông minh cho các ứng dụng LLM (Large Language Model), phân luồng request giữa 2 điểm:
- **Cloud (Qwen 7B)**: Mô hình to, thông minh hơn, nhưng bị ảnh hưởng nặng bởi độ trễ mạng (Network Latency) và chi phí cao.
- **Edge (Qwen 1.5B)**: Mô hình nhỏ, kém thông minh hơn, nhưng tốc độ phản hồi cực nhanh, không phụ thuộc vào mạng, chạy trực tiếp tại biên.

**Bài toán giải quyết:** Làm sao để *cân bằng* giữa Chất lượng (Quality) và Độ trễ (Latency)? Khi mạng lag, thà dùng mô hình nhỏ để có kết quả ngay, còn hơn chờ mô hình lớn quay đều.

---

## 2. Kiến Trúc Vận Hành (Lifecycle of a Request)
Hội đồng rất hay hỏi: *"Khi người dùng bấm Gửi, luồng dữ liệu đi thế nào?"*

1. **User (Web UI)** gửi request kèm `request_tag` (vd: `high_quality` hoặc `fast_ok`) lên **Gateway**.
2. **Gateway** tạm giữ request và gọi điện hỏi **Orchestrator** (Bộ não trung tâm).
3. **Orchestrator** chạy thuật toán tính điểm và hỏi **OPA** (Open Policy Agent) xem có luật an toàn nào bị vi phạm không. Chốt kết quả: Chọn Cloud hay Edge.
4. **Gateway** nhận quyết định, forward (proxy) luồng dữ liệu qua **Toxiproxy** (công cụ giả lập mạng) rồi mới tới **Ollama** (Cloud hoặc Edge).
5. **Ollama** chạy Inference (suy luận LLM) và trả kết quả về UI.

> [!TIP]
> **Điểm ăn tiền:** Việc tách biệt hoàn toàn **Control Plane** (Gateway, Orchestrator) và **Data Plane** (Luồng dữ liệu đi qua Toxiproxy và Ollama). Orchestrator đưa ra quyết định định tuyến mà không cần đọc nội dung prompt của user, đảm bảo tính **Privacy-Preserving** (Bảo mật dữ liệu).

---

## 3. Thuật Toán Định Tuyến (The Brain)
Hệ thống sử dụng kiến trúc **Two-Tier Agentic Orchestration (Mô hình 2 Tầng)**:

### Tầng 1: Strategic Agent (Chiến lược gia)
- **Tần suất chạy:** 10 giây / lần (chạy ngầm background).
- **Nhiệm vụ:** Nhìn bức tranh toàn cảnh. Đánh giá xu hướng mạng, CPU, và quyết định "Trạng thái hệ thống" (Master Plan) như `STATE_NORMAL`, `STATE_DEGRADED` (Mạng đang xuống cấp), hoặc `STATE_BURST` (Lưu lượng đang bùng nổ).

### Tầng 2: Tactical Agent (Lính thực thi)
- **Tần suất chạy:** Mỗi khi có request đến (tính bằng mili-giây).
- **Nhiệm vụ:** Tính điểm cho Cloud và Edge bằng công thức:
  `Điểm = Trọng số Chất lượng + Điểm Độ trễ + Điểm Hàng đợi (Inflight) + Điểm Tính toán (CPU/GPU)`
- Nó lấy dữ liệu từ một **Bộ nhớ đệm (In-Memory Cache)** phi đồng bộ. Việc cache này giúp định tuyến mất `O(1)` thời gian, không làm chậm request của user.

---

## 4. Ràng Buộc An Toàn (The Shield - OPA)
Dù Tactical Agent tính điểm Edge cao hơn, quyết định vẫn có thể bị "phủ quyết" bởi OPA.

**Tại sao dùng OPA (Open Policy Agent)?**
Viết luật bằng ngôn ngữ `Rego`. Giúp chúng ta thay đổi các giới hạn an toàn (SLA limits, CPU max) trong lúc hệ thống đang chạy mà không cần sửa code Python. (Tiêu chuẩn Enterprise).

**Các luật (Rules) chính:**
- Không cho qua nếu hàng đợi Gateway > 50 (Rule 1).
- Không cho qua nếu CPU Edge > 92% hoặc GPU Cloud > 90% (Rule 2).
- Không cho qua nếu `predicted_latency` (độ trễ dự báo) > `SLA_target` (Rule 3).
- **Fail-Open Mechanism**: Nếu OPA server bị sập/timeout, Gateway sẽ **Bypass** (cho qua luôn) thay vì ném lỗi 500 cho user. Nguyên lý: *"Thà phân luồng sai còn hơn làm sập dịch vụ"*.

---

## 5. Đánh Giá Khách Quan (Benchmark Engine)
Đây là cách bạn chứng minh luận văn không chỉ "nói suông":

- **Toxiproxy:** Tiêm "độc" vào mạng. Mạng GOOD (trễ 20ms). Mạng BAD (trễ 350ms, giật lag 60ms).
- **Locust:** Bắn hàng ngàn request cùng lúc để ép tải hệ thống (Low Load / High Load).
- **Isolation:** Tự động reset môi trường, warm-up mô hình trước mỗi bài test để đảm bảo "Cold Start" không làm nhiễu kết quả.
- **Kết quả thu được:** Chiến lược **PROPOSED** của chúng ta tự động chuyển bớt traffic sang Edge khi mạng BAD, giúp duy trì tỷ lệ rớt SLA thấp nhất so với các chiến lược tĩnh (Cloud-only, Edge-only, Round-robin). Có cả cơ chế **Circuit Breaker** (ngắt mạch) bảo vệ Gateway khi mô hình chưa kịp khởi động.

---

## 6. Kịch Bản Phản Biện (Defense Arsenal)
Hội đồng có thể hỏi những câu "xoáy" sâu vào các hạn chế. Đây là cách trả lời:

> [!WARNING]
> **Câu hỏi 1:** "Độ trễ dự báo (`predicted_latency`) của em đã tính thời gian suy luận (inference time) của LLM chưa?"
> **Trả lời:** Dạ chưa ạ. Hiện tại `predicted_latency` mới chỉ phản ánh **độ trễ mạng (Network Latency)** từ Toxiproxy. Do thời gian suy luận của LLM phụ thuộc rất nhiều vào độ dài của prompt và cấu trúc câu, việc dự đoán chính xác inference time đòi hỏi một hệ thống ML thứ 2 rất phức tạp. Đây là một proxy signal và em đã ghi nhận nó trong phần "Known Limitations" (Hướng phát triển tương lai) của luận văn.

> [!WARNING]
> **Câu hỏi 2:** "Làm sao em biết được hàng đợi bên trong Ollama đang là bao nhiêu?"
> **Trả lời:** Ollama hiện tại không expose (cung cấp) API để xem hàng đợi nội bộ. Do đó, hệ thống của em dùng `gateway_inflight` (số lượng request đang được Gateway xử lý và chờ phản hồi) làm một **Proxy Metric** (Thước đo đại diện). Khi Gateway tắc nghẽn, nghĩa là Ollama bên dưới đang quá tải.

> [!WARNING]
> **Câu hỏi 3:** "Tại sao chế độ CPU-only lại chạy chậm thế?"
> **Trả lời:** LLM bản chất là các phép toán ma trận khổng lồ. GPU có hàng ngàn nhân CUDA được sinh ra để tính toán song song, trong khi CPU chỉ có vài chục nhân. Bản demo trên máy không có GPU (chạy CPU-only) chỉ để chứng minh luồng định tuyến và logic Gateway hoạt động, còn kết quả Benchmark trong báo cáo đã được chạy 100% trên phần cứng có GPU ạ.

---

## 7. Lời Khuyên Khi Báo Cáo
1. **Bắt đầu bằng Demo:** Mở Web UI, thử 2 câu chat (1 câu chọn Edge, 1 câu chọn Cloud do mạng/chất lượng), cho hội đồng thấy hệ thống thực sự "sống".
2. **Khoe Benchmark:** Chuyển ngay sang trình chiếu biểu đồ `routing_distribution.png` và `sla_violations.png`. Hội đồng thích những đồ thị có số liệu khoa học đo đạc cụ thể bằng Locust + Toxiproxy hơn là đọc đống code Python.
3. **Thành thật với điểm yếu:** Nếu bị hỏi trúng mục Known Limitations, hãy dùng ngay các câu trả lời ở phần 6. Việc biết rõ giới hạn của hệ thống chứng tỏ bạn là một kỹ sư thực tế.
