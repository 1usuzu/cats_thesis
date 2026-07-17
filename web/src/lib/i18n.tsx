"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

type Language = "EN" | "VI";

type Translations = {
  [key in Language]: {
    [key: string]: string;
  };
};

const translations: Translations = {
  EN: {
    "nav_overview": "Overview",
    "nav_console": "Interactive Console",
    "nav_explain": "Route Explainability",
    "nav_cost": "Cost Analysis",
    "nav_tuning": "Parameter Tuning",
    "nav_telemetry": "Telemetry Stream",
    "nav_policy": "Policy Sandbox",
    "system_online": "System Online",
    "api_err": "API Error",
    "conn_failed": "Connection failed",
    "api_key_placeholder": "API Key",
    "strategy": "Routing Strategy",
    "request_label": "Request Tag",
    "clear_history": "Clear History",
    "recent_reqs": "Recent Requests",
    "no_telemetry": "No routing telemetry available yet. Use the Interactive Console.",
    "sys_status": "System Status",
    "edge_status": "Edge Status",
    "cloud_status": "Cloud Status",
    "opa_safety": "OPA Safety",
    "operational": "OPERATIONAL",
    "online": "ONLINE",
    "enforcing": "ENFORCING",
    "gw_healthy": "Gateway healthy",
    "inspect_req": "Inspect Request",
    "decision_summary": "Decision Summary",
    "sel_route": "Selected Route",
    "model": "Model",
    "score_diff": "Score Difference",
    "primary_reason": "Primary Reason",
    "decision_pipeline": "Decision Pipeline",
    "req_context": "Request Context",
    "scoring": "Scoring",
    "opa_policy": "OPA Policy",
    "output": "Output",
    "telemetry_snap": "Telemetry Snapshot",
    "alt_route": "Alternative Route",
    "reason_edge": "Latency SLA requirement met by Edge",
    "reason_cloud": "Complex task required Cloud capability",
    "health_desc": "Granular runtime signals affecting routing decisions.",
    "gw_queue": "Gateway Queue",
    "edge_cpu": "Edge Node CPU",
    "net_latency": "Network Latency",
    "proxy_status": "Proxy Status",
    "console_desc": "Send requests to the Gateway and see how they are routed.",
    "enter_prompt": "Enter your prompt...",
    "processing": "Processing via Gateway...",
    "no_resp": "No response returned.",
    "cost_desc": "Cost breakdown and financial metrics for routing decisions.",
    "cloud_exp_cost": "Cloud Expected Cost",
    "edge_exp_cost": "Edge Expected Cost",
    "optimal_route": "Optimal Route (by Score)",
    "optimal_condition_met": "Optimal Condition Met",
    "optimal_condition_failed": "Optimal Condition Failed (Safety Override)",
    
    // Policy Sandbox
    "policy_desc": "LLM-proposed Rego policy modifications. Must be validated by Critic Agent before human approval.",
    "btn_simulate": "Simulate Policy Proposal (LLM)",
    "val_status": "Validation Status",
    "val_validating": "VALIDATING...",
    "val_desc": "Critic Agent is analyzing the proposed Rego policy for syntax errors and logical flaws...",
    "btn_approve": "Approve & Deploy",
    "btn_reject": "Reject",
    "btn_dismiss": "Dismiss Proposal",
    "active_policy": "Active Rego Policy",
    "proposed_policy": "Proposed Rego Policy",
    "no_proposals": "No pending policy proposals.",
    "opa_stable": "The current Open Policy Agent (OPA) routing rules are stable.",
    "active_policy_deployed": "Active Rego Policy (Deployed)",

    // Telemetry
    "tel_paused": "Paused",
    "tel_live": "Live Stream",
    "tel_raw": "Raw Telemetry Stream",
    "tel_waiting": "Waiting for telemetry signals...",
    "tel_req_in_flight": "Requests in-flight",
    "tel_cpu_load": "Local GPU/CPU load",
    "tel_net_delay": "Toxiproxy network delay",
    "tel_proxy_cp": "Toxiproxy Control Plane",

    // Cost
    "cost_cloud_exp": "Cloud Expected Cost (Gemini Flash)",
    "cost_base_api": "Base API Cost",
    "cost_net_risk": "Network Overhead & Retry Risk",
    "cost_edge_exp": "Edge Expected Cost (Local GPU)",
    "cost_base_hw": "Base Hardware Cost",
    "cost_sla_risk": "SLA Miss & Capacity Risk",
    "cost_hist": "Historical Cost Overview",
    "cost_ts": "Timestamp",
    "cost_req_id": "Request ID",
    "cost_tag": "Tag",
    "cost_route": "Route",

    // Tuning
    "tuning_desc": "Monitor Auto-Tuning heuristics and Canary validation in real-time.",
    "tuning_ai_active": "AI Tuning Agent Active",
    "tuning_prod_w": "Production Weights",
    "tuning_traffic": "TRAFFIC",
    "tuning_canary_w": "Canary Weights",
    "tuning_testing": "TESTING",
    "tuning_idle": "IDLE",
    "tuning_expl_title": "Tuning Agent Explanation:",
    "tuning_expl_1": "The AI Tuning Agent continuously observes telemetry metrics (latency, queue depth, error rates) in the background. When it detects performance degradation, it proposes new routing weights (Canary Weights) and routes 10% of traffic to validate them.",
    "tuning_expl_2": "If the canary traffic shows improved SLA compliance, the weights are automatically promoted to Production. If not, they are rolled back instantly."
  },
  VI: {
    "nav_overview": "Tổng Quan",
    "nav_console": "Bảng Điều Khiển Tương Tác",
    "nav_explain": "Giải Thích Định Tuyến",
    "nav_cost": "Phân Tích Chi Phí",
    "nav_tuning": "Tinh Chỉnh Tham Số",
    "nav_telemetry": "Luồng Telemetry",
    "nav_policy": "Policy Sandbox",
    "system_online": "Hệ Thống Trực Tuyến",
    "api_err": "Lỗi API",
    "conn_failed": "Kết nối thất bại",
    "api_key_placeholder": "Khóa API",
    "strategy": "Chiến Lược Định Tuyến",
    "request_label": "Gắn Nhãn Yêu Cầu",
    "clear_history": "Xóa Lịch Sử",
    "recent_reqs": "Các Yêu Cầu Gần Đây",
    "no_telemetry": "Chưa có dữ liệu định tuyến. Vui lòng sử dụng Bảng Điều Khiển Tương Tác.",
    "sys_status": "Trạng Thái Hệ Thống",
    "edge_status": "Trạng Thái Edge",
    "cloud_status": "Trạng Thái Cloud",
    "opa_safety": "Bảo Mật OPA",
    "operational": "HOẠT ĐỘNG",
    "online": "TRỰC TUYẾN",
    "enforcing": "ĐANG ÁP DỤNG",
    "gw_healthy": "Gateway ổn định",
    "inspect_req": "Kiểm Tra Yêu Cầu",
    "decision_summary": "Tóm Tắt Quyết Định",
    "sel_route": "Tuyến Đã Chọn",
    "model": "Mô Hình",
    "score_diff": "Chênh Lệch Điểm",
    "primary_reason": "Lý Do Chính",
    "decision_pipeline": "Tiến Trình Quyết Định",
    "req_context": "Ngữ Cảnh",
    "scoring": "Chấm Điểm",
    "opa_policy": "Chính Sách OPA",
    "output": "Kết Quả",
    "telemetry_snap": "Dữ Liệu Hệ Thống",
    "alt_route": "Tuyến Dự Phòng",
    "reason_edge": "Edge đáp ứng đủ yêu cầu về độ trễ (SLA)",
    "reason_cloud": "Tác vụ phức tạp cần năng lực tính toán của Cloud",
    "health_desc": "Các tín hiệu chi tiết tại thời gian chạy ảnh hưởng đến định tuyến.",
    "gw_queue": "Hàng Đợi Gateway",
    "edge_cpu": "CPU của Edge",
    "net_latency": "Độ Trễ Mạng (Latency)",
    "proxy_status": "Trạng Thái Proxy",
    "console_desc": "Gửi yêu cầu tới Gateway và xem cách chúng được định tuyến.",
    "enter_prompt": "Nhập câu hỏi của bạn...",
    "processing": "Đang xử lý qua Gateway...",
    "no_resp": "Không có phản hồi.",
    "cost_desc": "Phân tích rủi ro và ước tính chi phí định tuyến theo Google Gemini Pricing.",
    "cloud_exp_cost": "Chi Phí Kỳ Vọng (Cloud)",
    "edge_exp_cost": "Chi Phí Kỳ Vọng (Edge)",
    "optimal_route": "Điều Kiện Tuyến Tối Ưu",
    "optimal_condition_met": "Thỏa mãn (Dựa trên điểm số cao nhất)",
    "optimal_condition_failed": "Bị Từ Chối (Do vi phạm OPA/An toàn)",

    // Policy Sandbox
    "policy_desc": "Chính sách định tuyến do LLM đề xuất. Cần được Critic Agent xác thực trước khi người dùng phê duyệt.",
    "btn_simulate": "Mô phỏng Đề xuất (LLM)",
    "val_status": "Trạng thái xác thực",
    "val_validating": "ĐANG KIỂM TRA...",
    "val_desc": "Critic Agent đang phân tích các lỗi cú pháp và logic trong Rego policy...",
    "btn_approve": "Phê duyệt & Áp dụng",
    "btn_reject": "Từ chối",
    "btn_dismiss": "Bỏ qua đề xuất",
    "active_policy": "Policy Hiện Tại",
    "proposed_policy": "Policy Đề Xuất",
    "no_proposals": "Không có đề xuất Policy nào đang chờ duyệt.",
    "opa_stable": "Luật định tuyến Open Policy Agent (OPA) hiện tại đang hoạt động ổn định.",
    "active_policy_deployed": "Policy Hiện Tại (Đã áp dụng)",

    // Telemetry
    "tel_paused": "Đã tạm dừng",
    "tel_live": "Trực tiếp",
    "tel_raw": "Dữ liệu Telemetry thô (JSON)",
    "tel_waiting": "Đang chờ tín hiệu telemetry...",
    "tel_req_in_flight": "Số lượng Request đang xử lý",
    "tel_cpu_load": "Tải CPU/GPU cục bộ",
    "tel_net_delay": "Độ trễ giả lập bởi Toxiproxy",
    "tel_proxy_cp": "Control Plane của Toxiproxy",

    // Cost
    "cost_cloud_exp": "Chi Phí Kỳ Vọng Cloud (Gemini Flash)",
    "cost_base_api": "Chi phí API gốc",
    "cost_net_risk": "Rủi ro mạng & Tải lại",
    "cost_edge_exp": "Chi Phí Kỳ Vọng Edge (GPU Cục bộ)",
    "cost_base_hw": "Chi phí phần cứng gốc",
    "cost_sla_risk": "Rủi ro vi phạm SLA & Dung lượng",
    "cost_hist": "Lịch sử Chi Phí",
    "cost_ts": "Thời gian",
    "cost_req_id": "Mã Yêu Cầu",
    "cost_tag": "Nhãn",
    "cost_route": "Tuyến",

    // Tuning
    "tuning_desc": "Giám sát thuật toán Auto-Tuning và kiểm thử Canary theo thời gian thực.",
    "tuning_ai_active": "Tuning Agent Đang Hoạt Động",
    "tuning_prod_w": "Trọng số Sản xuất",
    "tuning_traffic": "LƯU LƯỢNG",
    "tuning_canary_w": "Trọng số Canary",
    "tuning_testing": "ĐANG THỬ NGHIỆM",
    "tuning_idle": "ĐANG CHỜ",
    "tuning_expl_title": "Giải thích về Tuning Agent:",
    "tuning_expl_1": "AI Tuning Agent liên tục theo dõi các chỉ số telemetry (độ trễ, hàng đợi, lỗi). Khi phát hiện suy giảm hiệu năng, nó sẽ đề xuất trọng số mới (Canary Weights) và trích 10% lưu lượng để kiểm thử.",
    "tuning_expl_2": "Nếu lưu lượng canary cải thiện độ tuân thủ SLA, các trọng số này sẽ được đưa lên Sản xuất. Ngược lại, chúng sẽ bị hủy bỏ ngay lập tức."
  },
};

type I18nContextType = {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: string) => string;
};

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Language>("VI");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("cats_lang") as Language;
    if (saved && (saved === "EN" || saved === "VI")) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLang(saved);
    }
    setMounted(true);
  }, []);

  const handleSetLang = (newLang: Language) => {
    setLang(newLang);
    localStorage.setItem("cats_lang", newLang);
  };

  const t = (key: string) => {
    return translations[lang][key] || key;
  };

  if (!mounted) {
    return null;
  }

  return (
    <I18nContext.Provider value={{ lang, setLang: handleSetLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
