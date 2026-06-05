import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
GATEWAY_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{GATEWAY_URL}/v1/chat"
ADMIN_ENDPOINT = f"{GATEWAY_URL}/admin/strategy"

st.set_page_config(page_title="CATS Thesis Demo", layout="wide")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_strategy" not in st.session_state:
    st.session_state.current_strategy = "PROPOSED"

# --- Sidebar ---
with st.sidebar:
    st.title("CATS Control Panel")
    api_key = st.text_input("API Key", type="password", help="Enter the X-API-Key for the Gateway.", value=os.getenv("CATS_API_KEY", ""))
    
    strategy_labels = {
        "PROPOSED": "PROPOSED (Smart Routing)",
        "BASELINE-1": "BASELINE-1 (Round-Robin)",
        "BASELINE-2": "BASELINE-2 (Cloud-Only)",
        "BASELINE-3": "BASELINE-3 (Edge-Only)",
    }
    
    st.markdown("### Routing Strategy")
    strategies = ["PROPOSED", "BASELINE-1", "BASELINE-2", "BASELINE-3"]
    selected_strategy = st.selectbox(
        "Select Gateway Strategy", 
        strategies, 
        index=strategies.index(st.session_state.current_strategy),
        format_func=lambda x: strategy_labels.get(x, x)
    )
    
    strategy_descriptions = {
        "PROPOSED": "Dynamically routes to Edge if Cloud is congested or network is unstable.",
        "BASELINE-1": "Alternates requests evenly between Cloud and Edge, ignoring real-time metrics.",
        "BASELINE-2": "Sends all requests to high-capacity Cloud models, ignoring Edge resources.",
        "BASELINE-3": "Sends all requests to local Edge models, prioritizing privacy over capacity.",
    }
    st.info(strategy_descriptions.get(selected_strategy, ""))
    
    if selected_strategy != st.session_state.current_strategy:
        headers = {"X-API-Key": api_key} if api_key else {}
        try:
            res = requests.post(ADMIN_ENDPOINT, json={"strategy": selected_strategy}, headers=headers, timeout=5)
            if res.status_code == 200:
                st.session_state.current_strategy = selected_strategy
                st.rerun()  # Force immediate refresh to prevent 2-click delay and remove log
            else:
                pass  # Silently ignore as per user request
        except requests.exceptions.RequestException as e:
            pass  # Silently ignore as per user request
            
    st.info(f"**Active Strategy:**\n\n`{st.session_state.current_strategy}`")
    
    st.markdown("### Request Options")
    request_tag = st.selectbox(
        "Simulated Context (Tag)", 
        ["default", "fast_ok", "high_quality"],
        help="Simulates different computational complexities for the AI, helping test how the gateway routes various workload types."
    )
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- Main Chat Area ---
st.title("CATS Live Inference Demo")
st.markdown("Interactive UI for demonstrating Cloud-Edge LLM Routing.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "metrics" in msg:
            st.markdown(msg["metrics"], unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Enter your prompt for the CATS Gateway..."):
    # 1. Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Call Gateway API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        metrics_placeholder = st.empty()
        
        headers = {"X-API-Key": api_key} if api_key else {}
        payload = {
            "prompt": prompt,
            "request_tag": request_tag
        }
        
        try:
            with st.spinner("Routing request via CATS Gateway..."):
                res = requests.post(CHAT_ENDPOINT, json=payload, headers=headers, timeout=120)
                
            if res.status_code == 200:
                data = res.json()
                api_resp = data.get("data", {})
                content = api_resp.get("response", "No response content returned.")
                route_info = api_resp.get("route", {})
                
                # Display response
                message_placeholder.markdown(content)
                
                # Build metrics badge
                site = route_info.get("site", "unknown").lower()
                latency = route_info.get("total_inference_ms", 0)
                model = route_info.get("model", "unknown")
                strategy_used = route_info.get("strategy", "unknown")
                
                # Colors: Blue for cloud, Green for edge
                bg_color = "#2ecc71" if site == "edge" else "#3498db" if site == "cloud" else "#95a5a6"
                
                badge_html = f"""
                <div style="margin-top: 15px; padding: 10px 15px; border-radius: 8px; background-color: {bg_color}; color: white; display: inline-block; font-family: monospace; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <b>Route:</b> {site.upper()} &nbsp;|&nbsp; <b>Time:</b> {latency} ms &nbsp;|&nbsp; <b>Model:</b> {model} &nbsp;|&nbsp; <b>Strategy:</b> {strategy_used}
                </div>
                """
                metrics_placeholder.markdown(badge_html, unsafe_allow_html=True)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": content,
                    "metrics": badge_html
                })
            else:
                error_text = f"**API Error {res.status_code}:**\n```json\n{res.text}\n```"
                message_placeholder.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})
                
        except requests.exceptions.RequestException as e:
            error_text = f"**Connection failed.** Is the Gateway running at `{GATEWAY_URL}`?\n\nError details: `{e}`"
            message_placeholder.error(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
