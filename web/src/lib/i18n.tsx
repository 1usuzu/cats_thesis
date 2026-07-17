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
    "cost_desc": "Chi tiết phân bổ chi phí dựa trên xác suất Retry & SLA.",
    "cloud_exp_cost": "Chi Phí Kỳ Vọng (Cloud)",
    "edge_exp_cost": "Chi Phí Kỳ Vọng (Edge)",
    "optimal_route": "Điều Kiện Tuyến Tối Ưu",
    "optimal_condition_met": "Thỏa mãn (Dựa trên điểm số cao nhất)",
    "optimal_condition_failed": "Bị Từ Chối (Do vi phạm OPA/An toàn)",
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
