import streamlit as st
import requests
import json
import os
import time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
GATEWAY_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{GATEWAY_URL}/v1/chat"
ADMIN_ENDPOINT = f"{GATEWAY_URL}/admin/strategy"
GATEWAY_HEALTH_ENDPOINT = f"{GATEWAY_URL}/health/ready"

ORCHESTRATOR_URL = "http://localhost:8080"
TELEMETRY_ENDPOINT = f"{ORCHESTRATOR_URL}/telemetry"


st.set_page_config(page_title="CATS Control Plane", layout="wide", initial_sidebar_state="expanded")

# --- Translations ---
TRANSLATIONS = {
    "EN": {
        "cats_control_plane": "CATS Control Plane",
        "api_key": "API Key",
        "routing_strategy": "Routing Strategy",
        "request_tag": "Request Tag",
        "clear_history": "Clear History",
        "nav_overview": "Overview",
        "nav_explain": "Route Explainability",
        "nav_console": "Interactive Console",
        "nav_telemetry": "Health & Telemetry",
        
        "overview_desc": "Real-time system status and snapshot metrics.",
        "sys_status": "System Status",
        "edge_status": "Edge Status",
        "cloud_status": "Cloud Status",
        "opa_safety": "OPA Safety",
        "operational": "OPERATIONAL",
        "online": "ONLINE",
        "enforcing": "ENFORCING",
        "gw_healthy": "Gateway healthy",
        "recent_reqs": "Recent Requests",
        
        "no_telemetry": "No routing telemetry available yet. Use the Interactive Console.",
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
        "api_err": "API Error",
        "conn_failed": "Connection failed.",
        "lang": "Language",
    },
    "VI": {
        "cats_control_plane": "Bảng Điều Khiển CATS",
        "api_key": "Khóa API",
        "routing_strategy": "Chiến Lược Định Tuyến",
        "request_tag": "Gắn Nhãn Yêu Cầu",
        "clear_history": "Xóa Lịch Sử",
        "nav_overview": "Tổng Quan",
        "nav_explain": "Giải Thích Định Tuyến",
        "nav_console": "Bảng Điều Khiển Tương Tác",
        "nav_telemetry": "Sức Khỏe Hệ Thống",
        
        "overview_desc": "Trạng thái hệ thống thời gian thực và số liệu hiện tại.",
        "sys_status": "Trạng Thái Hệ Thống",
        "edge_status": "Trạng Thái Edge",
        "cloud_status": "Trạng Thái Cloud",
        "opa_safety": "Bảo Mật OPA",
        "operational": "HOẠT ĐỘNG",
        "online": "TRỰC TUYẾN",
        "enforcing": "ĐANG ÁP DỤNG",
        "gw_healthy": "Gateway ổn định",
        "recent_reqs": "Các Yêu Cầu Gần Đây",
        
        "no_telemetry": "Chưa có dữ liệu định tuyến. Vui lòng sử dụng Bảng Điều Khiển Tương Tác.",
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
        "api_err": "Lỗi API",
        "conn_failed": "Kết nối thất bại.",
        "lang": "Ngôn ngữ / Language",
    }
}

def t(key):
    lang = st.session_state.get("language", "VI")
    return TRANSLATIONS[lang].get(key, key)

# --- Custom CSS ---
def inject_css():
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
    html, body, p, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText { font-family: 'Fira Sans', sans-serif !important; }
    code, pre, .mono-font, .metric-value, .timeline-time { font-family: 'Fira Code', monospace !important; }
    
    /* Remove vertical scrolling by compressing margins/padding */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 95% !important;
    }
    
    h1 {
        margin-bottom: 0.5rem !important;
        padding-bottom: 0 !important;
        font-size: 1.8rem !important;
    }
    
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    .stSelectbox {
        margin-bottom: 0 !important;
    }
    
    .metric-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: left;
    }
    
    /* Flowchart / Pipeline layout for Explainability */
    .pipeline-container {
        display: flex;
        align-items: stretch;
        justify-content: space-between;
        gap: 8px;
        margin-top: 5px;
        overflow-x: hidden;
    }
    .pipeline-step {
        flex: 1;
        min-width: 140px;
        background-color: transparent;
        border: 2px solid #3B82F6;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
        font-size: 0.9rem;
        position: relative;
    }
    .pipeline-arrow {
        flex: 0 0 20px;
        text-align: center;
        font-size: 20px;
        color: gray;
        opacity: 0.5;
        align-self: center;
    }
    
    /* JSON block compression */
    .stJson {
        font-size: 0.8rem;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# --- State Initialization ---
def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_strategy" not in st.session_state:
        st.session_state.current_strategy = "PROPOSED"
    if "telemetry_records" not in st.session_state:
        st.session_state.telemetry_records = []
    if "language" not in st.session_state:
        st.session_state.language = "VI"

# --- Helper Functions ---
def fetch_telemetry():
    try:
        res = requests.get(TELEMETRY_ENDPOINT, timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def fetch_gateway_health():
    try:
        res = requests.get(GATEWAY_HEALTH_ENDPOINT, timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def add_telemetry_record(prompt, request_tag, gateway_response, duration_ms):
    api_resp = gateway_response.get("data", {})
    route_info = api_resp.get("route", {})
    meta = gateway_response.get("meta", {})
    analysis = meta.get("routing_analysis", {})
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    req_id = f"REQ-{len(st.session_state.telemetry_records) + 1:04d}"
    
    final_scores = analysis.get("final_scores", {})
    opa_violations = analysis.get("opa_violations", [])
    
    record = {
        "request_id": req_id,
        "timestamp": timestamp,
        "prompt": prompt,
        "tag": request_tag,
        "strategy": meta.get("strategy", "UNKNOWN"),
        "cloud_score": final_scores.get("cloud", 0.0) if analysis else 0.0,
        "edge_score": final_scores.get("edge", 0.0) if analysis else 0.0,
        "tier1_state": analysis.get("tier1_state", "UNKNOWN") if analysis else "UNKNOWN",
        "opa_status": analysis.get("opa_status", "UNKNOWN") if analysis else "UNKNOWN",
        "opa_violations": opa_violations,
        "selected_route": route_info.get("site", "unknown").upper(),
        "selected_model": route_info.get("model", "unknown"),
        "latency_ms": route_info.get("total_inference_ms", duration_ms)
    }
    st.session_state.telemetry_records.append(record)

# --- Pages ---

def page_overview():
    st.title(t("nav_overview"))
    st.markdown(t("overview_desc"))
    st.divider()
    
    gw_health = fetch_gateway_health()
    tel = fetch_telemetry()
    
    sys_status_val = t("operational") if gw_health else "OFFLINE"
    gw_msg = t("gw_healthy") if gw_health else "Unreachable"
    
    edge_status_val = t("online") if gw_health and gw_health.get("checks", {}).get("edge_node") else "OFFLINE"
    cloud_status_val = t("online") if gw_health and gw_health.get("checks", {}).get("cloud_node") else "OFFLINE"
    
    opa_status_val = t("enforcing") if tel else "UNKNOWN"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("sys_status"), sys_status_val, gw_msg)
    c2.metric(t("edge_status"), edge_status_val)
    c3.metric(t("cloud_status"), cloud_status_val)
    c4.metric(t("opa_safety"), opa_status_val)
    
    st.subheader(t("recent_reqs"))
    if st.session_state.telemetry_records:
        df = pd.DataFrame(st.session_state.telemetry_records)
        cols = ["timestamp", "request_id", "prompt", "tag", "selected_route", "latency_ms"]
        df = df[[c for c in cols if c in df.columns]]
        st.dataframe(df, hide_index=True)
    else:
        st.info(t("no_telemetry"))

def page_route_explainability():
    st.markdown(f"<h1 style='font-size: 1.5rem;'>{t('nav_explain')}</h1>", unsafe_allow_html=True)
    
    if not st.session_state.telemetry_records:
        st.info(t("no_telemetry"))
        return
        
    records = {r["request_id"]: f"{r['request_id']} ({r['tag']}) - {r['timestamp']}" for r in reversed(st.session_state.telemetry_records)}
    selected_id = st.selectbox(t("inspect_req"), options=list(records.keys()), format_func=lambda x: records[x], label_visibility="collapsed")
    
    rec = next((r for r in st.session_state.telemetry_records if r["request_id"] == selected_id), None)
    if not rec:
        return
        
    left_col, right_col = st.columns([1, 2.5])
    
    with left_col:
        st.markdown(f"**{t('decision_summary')}**")
        st.markdown(f"**Prompt:** *\"{rec['prompt']}\"*")
        st.markdown(f"**{t('sel_route')}:** `{rec['selected_route']}`<br/>**{t('model')}:** `{rec['selected_model']}`<br/>**{t('score_diff')}:** {abs(rec['cloud_score'] - rec['edge_score']):.3f}", unsafe_allow_html=True)
        
        primary_reason = t("reason_edge") if rec['selected_route'] == "EDGE" else t("reason_cloud")
        st.markdown(f"**{t('primary_reason')}:** {primary_reason}")
        
        st.markdown(f"<br/>**{t('alt_route')}**", unsafe_allow_html=True)
        alt_route = "CLOUD" if rec['selected_route'] == "EDGE" else "EDGE"
        alt_score = rec['cloud_score'] if alt_route == "CLOUD" else rec['edge_score']
        st.markdown(f"Fallback: **{alt_route}**<br/>Score: {alt_score:.3f}", unsafe_allow_html=True)
        
        st.markdown(f"<br/>**{t('telemetry_snap')}**", unsafe_allow_html=True)
        st.json({
            "Tier1_Network": rec['tier1_state'],
            "Prompt_Complexity": "Moderate"
        })

    with right_col:
        st.markdown(f"**{t('decision_pipeline')}**")
        opa_color = "#10B981" if rec['opa_status'] == "enforced" and not rec['opa_violations'] else "#EF4444"
        flow_html = f"""
        <div class="pipeline-container">
            <div class="pipeline-step">
                <strong>1. {t('req_context')}</strong><br/>
                Tag: {rec['tag']}<br/>
                Strategy: {rec['strategy']}
            </div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step">
                <strong>2. {t('scoring')}</strong><br/>
                Edge: {rec['edge_score']:.3f}<br/>
                Cloud: {rec['cloud_score']:.3f}
            </div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step" style="border-color: {opa_color}">
                <strong>3. {t('opa_policy')}</strong><br/>
                Status: {rec['opa_status'].upper()}<br/>
                Violations: {len(rec['opa_violations'])}
            </div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step" style="border-color: #3B82F6; background-color: rgba(59, 130, 246, 0.1);">
                <strong>4. {t('output')}</strong><br/>
                Route: {rec['selected_route']}<br/>
                Latency: {rec['latency_ms']}ms
            </div>
        </div>
        """
        st.markdown(flow_html, unsafe_allow_html=True)

def page_telemetry():
    st.title(t("nav_telemetry"))
    st.markdown(t("health_desc"))
    st.divider()
    
    tel = fetch_telemetry()
    if tel:
        metrics = tel.get("metrics", {})
        cloud_q = metrics.get("cloud_gateway_inflight", 0)
        edge_q = metrics.get("edge_gateway_inflight", 0)
        total_q = cloud_q + edge_q
        
        edge_cpu = metrics.get("edge_cpu_util", 0)
        
        state = tel.get("tier1_state", {})
        proxy_val = "ACTIVE" if state else "UNKNOWN"
        latency = state.get("latency_ms", metrics.get("edge_latency_ms", 0)) if isinstance(state, dict) else metrics.get("edge_latency_ms", 0)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("gw_queue"), f"{total_q} in-flight")
        c2.metric(t("edge_cpu"), f"{edge_cpu:.1f}%")
        c3.metric(t("net_latency"), f"{latency} ms")
        c4.metric(t("proxy_status"), proxy_val)
    else:
        st.warning("Cannot fetch telemetry data from Orchestrator.")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("gw_queue"), "N/A")
        c2.metric(t("edge_cpu"), "N/A")
        c3.metric(t("net_latency"), "N/A")
        c4.metric(t("proxy_status"), "N/A")

def page_sandbox():
    st.markdown(f"### {t('nav_console')}")
    st.markdown(t("console_desc"))
    
    api_key = st.session_state.get("api_key", os.getenv("CATS_API_KEY", ""))
    request_tag = st.session_state.get("request_tag", "default")
    
    with st.container(height=500, border=False):
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    if prompt := st.chat_input(t("enter_prompt")):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            headers = {"X-API-Key": api_key} if api_key else {}
            payload = {"prompt": prompt, "request_tag": request_tag}
            
            start_t = time.time()
            try:
                with st.spinner(t("processing")):
                    res = requests.post(CHAT_ENDPOINT, json=payload, headers=headers, timeout=120)
                duration_ms = int((time.time() - start_t) * 1000)
                
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("data", {}).get("response", t("no_resp"))
                    message_placeholder.markdown(content)
                    st.session_state.messages.append({"role": "assistant", "content": content})
                    add_telemetry_record(prompt, request_tag, data, duration_ms)
                else:
                    error_text = f"**{t('api_err')} {res.status_code}:**\\n```json\\n{res.text}\\n```"
                    message_placeholder.error(error_text)
                    st.session_state.messages.append({"role": "assistant", "content": error_text})
                    
            except requests.exceptions.RequestException as e:
                error_text = f"**{t('conn_failed')}** Gateway error: `{e}`"
                message_placeholder.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})

# --- Main App ---
def main():
    init_state()
    inject_css()
    
    with st.sidebar:
        st.markdown(f"### {t('cats_control_plane')}")
        
        st.session_state.api_key = st.text_input(t("api_key"), type="password", value=os.getenv("CATS_API_KEY", ""))
        
        strategies = ["PROPOSED", "BASELINE-1", "BASELINE-2", "BASELINE-3"]
        selected_strategy = st.selectbox(
            t("routing_strategy"), 
            strategies, 
            index=strategies.index(st.session_state.current_strategy)
        )
        if selected_strategy != st.session_state.current_strategy:
            headers = {"X-API-Key": st.session_state.api_key} if st.session_state.api_key else {}
            try:
                res = requests.post(ADMIN_ENDPOINT, json={"strategy": selected_strategy}, headers=headers, timeout=5)
                if res.status_code == 200:
                    st.session_state.current_strategy = selected_strategy
                    st.rerun()
            except requests.exceptions.RequestException:
                pass
        
        st.session_state.request_tag = st.selectbox(t("request_tag"), ["default", "fast_ok", "high_quality"])
        
        if st.button(t("clear_history")):
            st.session_state.messages = []
            st.session_state.telemetry_records = []
            st.rerun()

    # Ngôn ngữ ở góc phải trên cùng
    c_empty, c_lang = st.columns([8.5, 1.5])
    with c_lang:
        lang = st.segmented_control(
            "Language",
            options=["VI", "EN"],
            default=st.session_state.language,
            label_visibility="collapsed"
        )
        if lang and lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()

    # Chỉ giữ lại các trang thực tế có chức năng
    pg = st.navigation([
        st.Page(page_sandbox, title=t("nav_console")),
        st.Page(page_route_explainability, title=t("nav_explain")),
        st.Page(page_overview, title=t("nav_overview")),
        st.Page(page_telemetry, title=t("nav_telemetry")),
    ])
    pg.run()

if __name__ == "__main__":
    main()
