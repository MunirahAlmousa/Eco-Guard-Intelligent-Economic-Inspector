import streamlit as st
import pandas as pd
import time
import base64
import os
import plotly.graph_objects as go
import concurrent.futures
import threading
from api_client import call_demographic_agent, call_financial_agent, call_manager_agent, analyze_record_parallel
from utils import record_to_dict, get_trust_color, get_status_emoji, format_issues, csv_to_records, export_to_excel

st.set_page_config(
    page_title="Eco-Guard | المفتش الاقتصادي الذكي",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def get_image_base64(filename):
    path = os.path.join(BASE_DIR, filename)
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

bg_b64 = get_image_base64("background.jpg")
logo_b64 = get_image_base64("logo.jpg")

@st.cache_data
def get_logo_media_type():
    for ext, mime in [("logo.png","image/png"),("logo.jpg","image/jpeg"),("logo.jpeg","image/jpeg")]:
        path = os.path.join(BASE_DIR, ext)
        if os.path.exists(path):
            import base64 as b64mod
            with open(path,"rb") as f:
                data = b64mod.b64encode(f.read()).decode()
            return data, mime
    return None, None

_logo_data, _logo_mime = get_logo_media_type()
if _logo_data:
    logo_b64 = _logo_data
    logo_mime = _logo_mime
else:
    logo_mime = "image/png"

bg_style = f"url('data:image/jpeg;base64,{bg_b64}')" if bg_b64 else "linear-gradient(135deg, #0f3d2e 0%, #1A6B52 100%)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;900&display=swap');
    * {{ font-family: 'Tajawal', sans-serif; }}
    .stMarkdown, .stMarkdown p, .section-title,
    .stSelectbox label, .stNumberInput label, .stTextInput label,
    .stRadio label, .stRadio > div,
    [data-testid="stSidebar"] .stMarkdown,
    .sidebar-section-title, .sidebar-agent-item,
    .agent-field, .agent-name, .score-label,
    .status-text, .status-sub, .agents-title,
    .header-title-ar, .header-top-text {{
        direction: rtl !important;
        text-align: right !important;
    }}
    input, textarea, select {{ direction: rtl !important; text-align: right !important; }}
    .stApp {{ background: {bg_style} center center / cover fixed !important; background-color: #0f3d2e !important; }}
    .block-container {{ padding-top: 0 !important; }}
    [data-testid="stSidebar"] {{ background: rgba(15,61,46,0.95) !important; backdrop-filter: blur(20px) !important; border-right: 1px solid rgba(31, 94, 82, 0.5) !important; display: block !important; visibility: visible !important; opacity: 1 !important; }}
    [data-testid="stSidebar"] * {{ color: rgba(255,255,255,0.85) !important; font-family: 'Tajawal', sans-serif !important; }}
    .sidebar-logo-box {{ text-align: center; padding: 0px 16px 14px 16px; border-bottom: 1px solid rgba(26,107,82,0.4); margin-bottom: 20px; margin-top: -12px; }}
    .sidebar-logo-box img {{ max-width: 140px; max-height: 100px; object-fit: contain; border-radius: 12px; }}
    .sidebar-logo-text {{ color: #ffffff !important; font-size: 18px; font-weight: 700; margin-top: 8px; display: block; }}
    .sidebar-section-title {{ color: rgba(255,255,255,0.4) !important; font-size: 9px; letter-spacing: 3px; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid rgba(26,107,82,0.35); }}
    .sidebar-agent-item {{ border-right: 3px solid #1A6B52; border-left: none !important; padding: 10px 14px 10px 10px; margin: 6px 0; font-size: 13px; color: rgba(255,255,255,0.85) !important; background: rgba(26,107,82,0.15); border-radius: 0 6px 6px 0; direction: rtl !important; text-align: right !important; }}
    [data-testid="stSidebar"] .stButton > button {{ background: rgba(26,107,82,0.2) !important; border: 1px solid rgba(26,107,82,0.5) !important; color: #ffffff !important; font-size: 13px !important; font-weight: 700 !important; font-family: 'Tajawal', sans-serif !important; padding: 8px 12px !important; box-shadow: none !important; letter-spacing: 0 !important; outline: none !important; }}
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{ border: 1px solid rgba(255,255,255,0.2) !important; background: rgba(255,255,255,0.08) !important; }}
    [data-testid="stSidebar"] .stButton > button:hover {{ background: rgba(26,107,82,0.5) !important; color: #ffffff !important; transform: none !important; box-shadow: none !important; }}
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{ background: #1A6B52 !important; border: 1px solid #1A6B52 !important; color: #ffffff !important; }}
    [data-testid="stSidebar"] [data-testid="column"] > div > [data-testid="stVerticalBlock"] {{ background: transparent !important; box-shadow: none !important; padding: 4px !important; border-radius: 0 !important; }}
    [data-testid="stSidebar"] .stSelectbox > div > div {{ background: rgba(26,107,82,0.3) !important; border: 1px solid rgba(26,107,82,0.6) !important; border-radius: 6px !important; }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span, [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div {{ color: #ffffff !important; }}
    .main-header {{ background: rgba(15,61,46,0.88); backdrop-filter: blur(16px); border-bottom: 1px solid rgba(26,107,82,0.5); margin-bottom: 20px; border-radius: 0 0 16px 16px; margin-left: 12px; margin-right: 12px; overflow: hidden; }}
    .header-top-bar {{ background: rgba(26,107,82,0.15); border-bottom: 1px solid rgba(255,255,255,0.06); padding: 5px 36px; display: flex; justify-content: space-between; align-items: center; direction: rtl; }}
    .header-top-text {{ color: rgba(255,255,255,0.4); font-size: 10px; letter-spacing: 2px; text-transform: uppercase; }}
    .header-main {{ padding: 18px 36px; display: flex; align-items: center; justify-content: space-between; direction: rtl; }}
    .header-left {{ display: flex; align-items: center; gap: 16px; direction: rtl; }}
    .header-emblem {{ width: 48px; height: 48px; border: 1.5px solid rgba(26,107,82,0.7); border-radius: 6px; display: flex; align-items: center; justify-content: center; background: rgba(26,107,82,0.2); overflow: hidden; }}
    .header-emblem img {{ width: 38px; height: 38px; object-fit: contain; border-radius: 10px; }}
    .header-title-ar {{ color: #ffffff !important; font-size: 19px; font-weight: 700; margin: 0; line-height: 1.3; }}
    .header-title-en {{ color: rgba(255,255,255,0.5) !important; font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase; margin: 0; font-weight: 300; }}
    .header-badge {{ border: 1px solid rgba(26,107,82,0.6); color: rgba(255,255,255,0.8) !important; padding: 5px 14px; font-size: 11px; letter-spacing: 1px; border-radius: 4px; background: rgba(26,107,82,0.2); }}
    .header-divider {{ height: 2px; background: linear-gradient(90deg, transparent 0%, #1A6B52 50%, transparent 100%); }}
    [data-testid="column"] > div > [data-testid="stVerticalBlock"] {{ background: rgba(255,255,255,0.92) !important; backdrop-filter: blur(20px) !important; border-radius: 12px !important; padding: 20px 24px 28px 24px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.18) !important; }}
    [data-testid="stSidebar"] [data-testid="column"] > div > [data-testid="stVerticalBlock"] {{ background: transparent !important; backdrop-filter: none !important; border-radius: 0 !important; padding: 2px !important; box-shadow: none !important; }}
    .section-title {{ color: #1A6B52 !important; font-size: 15px !important; font-weight: 800 !important; margin-bottom: 16px !important; padding-bottom: 10px !important; border-bottom: 2px solid #1A6B52 !important; display: block !important; }}
    [data-testid="column"] div[data-testid="stMarkdownContainer"] p {{ color: #1a1a1a !important; font-weight: normal !important; }}
    .stSelectbox label, .stNumberInput label, .stTextInput label {{ color: #2c2c2c !important; font-size: 12px !important; font-weight: 600 !important; }}
    .stSelectbox > div > div {{ background: #f5f7f6 !important; border: 1.5px solid #d0d8d6 !important; border-radius: 6px !important; color: #2c2c2c !important; }}
    .stTextInput > div > div, .stNumberInput > div > div {{ background: #f5f7f6 !important; border: 1.5px solid #d0d8d6 !important; border-radius: 6px !important; }}
    .stTextInput input, .stNumberInput input {{ background: transparent !important; border: none !important; color: #2c2c2c !important; font-family: 'Tajawal', sans-serif !important; font-size: 14px !important; }}
    input::placeholder {{ color: #aab4b2 !important; opacity: 1 !important; }}
    .stTextInput > div > div:focus-within, .stNumberInput > div > div:focus-within, .stSelectbox > div > div:focus-within {{ border-color: #1A6B52 !important; box-shadow: 0 0 0 2px rgba(26,107,82,0.2) !important; }}
    .stNumberInput button {{ background: #e8efed !important; border: none !important; color: #1A6B52 !important; }}
    .stNumberInput button:hover {{ background: #1A6B52 !important; color: #ffffff !important; }}
    .stSelectbox [data-baseweb="select"] {{ direction: rtl !important; }}
    .stSelectbox [data-baseweb="select"] > div:first-child {{ direction: rtl !important; text-align: right !important; }}
    [data-testid="stSidebar"] .stRadio > div {{ display: flex !important; flex-direction: column !important; align-items: flex-end !important; width: 100% !important; }}
    [data-testid="stSidebar"] .stRadio label {{ flex-direction: row-reverse !important; justify-content: flex-start !important; gap: 8px !important; width: auto !important; }}
    .stButton > button {{ background: #1A6B52 !important; color: #ffffff !important; border: none !important; border-radius: 6px !important; font-family: 'Tajawal', sans-serif !important; font-size: 15px !important; font-weight: 700 !important; letter-spacing: 1px !important; padding: 14px 28px !important; transition: all 0.3s ease !important; box-shadow: 0 4px 16px rgba(26,107,82,0.4) !important; }}
    .stButton > button:hover {{ background: #267a6b !important; box-shadow: 0 6px 20px rgba(26,107,82,0.6) !important; transform: translateY(-1px) !important; }}
    .stButton > button p, .stButton > button span {{ color: #ffffff !important; font-weight: 700 !important; }}
    .result-score-card {{ background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); border-radius: 12px; padding: 36px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }}
    .score-number {{ font-size: 80px; font-weight: 900; line-height: 1; margin-bottom: 10px; }}
    .score-label {{ color: #6b7c7a; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; }}
    .result-status-card {{ background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); border-top: 3px solid #1A6B52; border-radius: 12px; padding: 36px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }}
    .status-icon-large {{ font-size: 52px; line-height: 1; margin-bottom: 14px; }}
    .status-text {{ font-size: 20px; font-weight: 700; color: #1a1a1a; margin-bottom: 6px; }}
    .status-sub {{ color: #7a8c8a; font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; }}
    .agents-title {{ color: #1a1a1a !important; font-size: 14px !important; font-weight: 700 !important; margin: 32px 0 16px 0 !important; padding: 12px 20px 12px 12px !important; border-radius: 8px !important; background: rgba(255,255,255,0.88) !important; border-right: 4px solid #1A6B52 !important; border-left: none !important; box-shadow: 0 2px 12px rgba(0,0,0,0.12) !important; direction: rtl !important; text-align: right !important; }}
    .agent-result-card {{ background: rgba(255,255,255,0.95) !important; backdrop-filter: blur(20px) !important; border-top: 3px solid #1A6B52 !important; border-radius: 12px !important; padding: 20px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.18) !important; margin-bottom: 8px !important; }}
    .agent-result-card * {{ color: #1a1a1a !important; }}
    .agent-field-label {{ color: #8a9c9a !important; }}
    .agent-field-value {{ color: #1a1a1a !important; font-weight: 600 !important; }}
    .agent-name {{ color: #1A6B52 !important; font-weight: 700 !important; font-size: 13px; letter-spacing: 0.5px; }}
    .agent-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e8efed; direction: rtl !important; flex-direction: row !important; }}
    .agent-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
    .agent-field {{ display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #f0f4f3; font-size: 12px; direction: rtl !important; }}
    .agent-field[style*="border:none"] {{ display: block !important; }}
    .agent-field-label {{ color: #8a9c9a; }}
    .agent-field-value {{ color: #2c2c2c; font-weight: 600; }}
    .issue-badge {{ background: #fff8f0; border: 1px solid #f5c49a; border-right: 3px solid #F2A365; border-left: none !important; color: #8a4a00; padding: 7px 12px 7px 8px; border-radius: 4px; font-size: 12px; margin: 5px 0; direction: rtl !important; text-align: right !important; }}
    .recommendation-box {{ background: #f0f7f5; border: 1px solid #c0ddd8; border-right: 3px solid #1A6B52; border-left: none !important; padding: 12px 16px 12px 12px; border-radius: 4px; color: #1a3a34; font-size: 12px; line-height: 1.7; margin-top: 12px; direction: rtl !important; text-align: right !important; }}
    .step-indicator {{ background: rgba(26,107,82,0.15); border: 1px solid rgba(26,107,82,0.4); border-right: 4px solid #1A6B52; border-left: none !important; color: rgba(255,255,255,0.85); padding: 12px 18px 12px 14px; border-radius: 4px; font-size: 13px; margin: 6px 0; backdrop-filter: blur(8px); direction: rtl !important; text-align: right !important; }}
    [data-testid="stTextInput"] input[type="password"] {{ -webkit-text-security: disc !important; }}
    ::-webkit-credentials-auto-fill-button {{ display: none !important; }}
    .stAlert {{ background: rgba(255,255,255,0.92) !important; border-right: 4px solid #1A6B52 !important; border-radius: 8px !important; box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important; }}
    .stAlert * {{ color: #1a1a1a !important; font-weight: 600 !important; }}
    div[data-baseweb="tooltip"], div[role="tooltip"] {{ display: none !important; visibility: hidden !important; opacity: 0 !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}
    [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
    .stRadio label {{ color: rgba(255,255,255,0.8) !important; }}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<script>
function fixNumberInputs() {
    const containers = document.querySelectorAll('[data-testid="stNumberInput"] > div');
    containers.forEach(container => {
        const stepDown = container.querySelector('[data-testid="stNumberInputStepDown"]');
        const stepUp   = container.querySelector('[data-testid="stNumberInputStepUp"]');
        const inp      = container.querySelector('input[type="number"]');
        if (!stepDown || !stepUp || !inp) return;
        container.appendChild(stepDown);
        container.insertBefore(inp, stepDown);
        container.insertBefore(stepUp, inp);
    });
}
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(fixNumberInputs, 500);
    setTimeout(fixNumberInputs, 1500);
});
const obs = new MutationObserver(function() { fixNumberInputs(); });
obs.observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

from database import init_db, login_user, register_user, get_all_users, delete_user, log_analysis, get_audit_log
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "login_mode" not in st.session_state:
    st.session_state.login_mode = "login"
if "mode" not in st.session_state:
    st.session_state.mode = "إدخال يدوي"

if not st.session_state.logged_in:
    logo_img_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="max-width:110px; max-height:75px; object-fit:contain; border-radius:6px;">' if logo_b64 else '<span style="font-size:48px; color:#1A6B52;">◈</span>'

    st.markdown("""
    <style>
    .block-container { padding: 0 !important; max-width: 100% !important; }
    .login-card .stTextInput label { color: rgba(255,255,255,0.7) !important; font-size:13px !important; }
    .login-card .stTextInput > div > div { background: rgba(26,107,82,0.2) !important; border: 1px solid rgba(26,107,82,0.5) !important; border-radius:6px !important; }
    .login-card .stTextInput input { color: #ffffff !important; background: transparent !important; }
    .login-card .stButton > button { background: #1A6B52 !important; color:#fff !important; width:100% !important; border-radius:6px !important; font-size:15px !important; font-weight:700 !important; padding:12px !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div style="background:rgba(15,61,46,0.92);backdrop-filter:blur(28px);border:1px solid rgba(26,107,82,0.6);
            border-top:3px solid #1A6B52;border-radius:14px;padding:28px 28px 20px 28px;
            box-shadow:0 24px 64px rgba(0,0,0,0.7);text-align:center;margin-bottom:16px;">
            <div style="margin-bottom:10px;">{logo_img_html}</div>
            <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:2px;">Eco-Guard</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:1px;">المفتش الاقتصادي الذكي — هيئة الإحصاء العامة</div>
        </div>
        """, unsafe_allow_html=True)

        tab_col1, tab_col2 = st.columns(2)
        with tab_col1:
            if st.button("تسجيل الدخول", use_container_width=True,
                type="primary" if st.session_state.login_mode == "login" else "secondary"):
                st.session_state.login_mode = "login"
                st.rerun()
        with tab_col2:
            if st.button("حساب جديد", use_container_width=True,
                type="primary" if st.session_state.login_mode == "register" else "secondary"):
                st.session_state.login_mode = "register"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state.login_mode == "login":
            username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم", key="login_user")
            password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور", key="login_pass", autocomplete="new-password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("دخول", use_container_width=True, key="btn_login"):
                if username and password:
                    result = login_user(username, password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.current_user = result["username"]
                        st.session_state.user_role = result["role"]
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.error("يرجى إدخال اسم المستخدم وكلمة المرور")
        else:
            reg_error = st.empty()
            new_username = st.text_input("اسم المستخدم", placeholder="اختر اسم مستخدم", key="reg_user")
            new_password = st.text_input("كلمة المرور", type="password", placeholder="اختر كلمة مرور", key="reg_pass", autocomplete="new-password")
            confirm_password = st.text_input("تأكيد كلمة المرور", type="password", placeholder="أعد إدخال كلمة المرور", key="reg_confirm", autocomplete="new-password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("إنشاء حساب", use_container_width=True, key="btn_register"):
                if new_username and new_password and confirm_password:
                    if new_password != confirm_password:
                        reg_error.error("كلمات المرور غير متطابقة")
                    else:
                        result = register_user(new_username, new_password)
                        if result["success"]:
                            reg_error.success(result["message"] + " — يمكنك الدخول الآن")
                            st.session_state.login_mode = "login"
                            st.rerun()
                        else:
                            reg_error.error(result["message"])
                else:
                    reg_error.error("يرجى تعبئة جميع الحقول")

    st.stop()


logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:36px;height:36px;object-fit:contain;">' if logo_b64 else '◈'

st.markdown(f"""
<div class="main-header">
    <div class="header-top-bar">
        <span class="header-top-text">الهيئة العامة للإحصاء — المملكة العربية السعودية</span>
        <span class="header-top-text">General Authority for Statistics — KSA</span>
    </div>
    <div class="header-main">
        <div class="header-left">
            <div class="header-emblem">{logo_html}</div>
            <div>
                <p class="header-title-ar">المفتش الاقتصادي الذكي — Eco-Guard</p>
                <p class="header-title-en">Data Verification System — Household Survey</p>
            </div>
        </div>
        <div class="header-badge">نظام التحقق من بيانات المسح الأسري</div>
    </div>
    <div class="header-divider"></div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    if logo_b64:
        st.markdown(f"""
        <div class="sidebar-logo-box">
            <img src="data:image/jpeg;base64,{logo_b64}" alt="Eco-Guard Logo">
            <span class="sidebar-logo-text">المفتش الاقتصادي الذكي</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sidebar-logo-box">
            <span style="font-size:32px; color:#1A6B52;">◈</span>
            <span class="sidebar-logo-text">المفتش الاقتصادي الذكي</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<p class="sidebar-section-title">وضع التحليل</p>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("يدوي ", use_container_width=True, key="btn_manual",
            type="primary" if st.session_state.mode == "إدخال يدوي" else "secondary"):
            st.session_state.mode = "إدخال يدوي"
            st.rerun()
    with col_m2:
        if st.button("رفع ملف ", use_container_width=True, key="btn_csv",
            type="primary" if st.session_state.mode == "رفع ملف CSV" else "secondary"):
            st.session_state.mode = "رفع ملف CSV"
            st.rerun()
    mode = st.session_state.mode

    st.markdown("---")
    st.markdown('<p class="sidebar-section-title">وكلاء النظام</p>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-agent-item">الوكيل الديموغرافي<br><small style="opacity:0.5">يفحص العمر والتعليم والمهنة</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-agent-item">الوكيل المالي<br><small style="opacity:0.5">يفحص الدخل والإنفاق والكهرباء</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-agent-item">الوكيل القيادي<br><small style="opacity:0.5">يصدر درجة الموثوقية النهائية</small></div>', unsafe_allow_html=True)
    st.markdown("---")

    current = st.session_state.get("current_user", "")
    role = st.session_state.get("user_role", "user")
    role_label = "مدير النظام" if role == "admin" else "باحث ميداني"
    st.markdown(f'<div style="color:rgba(255,255,255,0.5);font-size:11px;text-align:center;margin-bottom:8px;">{role_label} — {current}</div>', unsafe_allow_html=True)

    if role == "admin":
        if "show_users" not in st.session_state:
            st.session_state.show_users = False
        if "show_audit" not in st.session_state:
            st.session_state.show_audit = False

        if st.button("⚙️ إدارة المستخدمين", use_container_width=True, key="btn_users"):
            st.session_state.show_users = not st.session_state.show_users
            st.session_state.show_audit = False
            st.rerun()
        if st.session_state.show_users:
            users = get_all_users()
            for u in users:
                uid, uname, urole, ucreated = u
                col_name, col_del = st.columns([3,1])
                with col_name:
                    label = "(مدير)" if urole == "admin" else "(باحث)"
                    st.markdown(f'<div style="color:rgba(255,255,255,0.8);font-size:12px;padding:4px 0;">{label} {uname}</div>', unsafe_allow_html=True)
                with col_del:
                    if urole != "admin":
                        if st.button("🗑", key=f"del_{uid}"):
                            delete_user(uid)
                            st.rerun()

        if st.button("📋 سجل العمليات", use_container_width=True, key="btn_audit"):
            st.session_state.show_audit = not st.session_state.show_audit
            st.session_state.show_users = False
            st.rerun()
        if st.session_state.show_audit:
            logs = get_audit_log(limit=20)
            if logs:
                for log in logs:
                    uname, action, timestamp, success = log
                    icon = "✅" if success else "❌"
                    st.markdown(f'<div style="color:rgba(255,255,255,0.7);font-size:10px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.1);">{icon} {uname} — {action}<br><span style="opacity:0.5">{timestamp}</span></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:rgba(255,255,255,0.5);font-size:11px;">لا يوجد سجلات</div>', unsafe_allow_html=True)

    if st.button("تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.user_role = None
        st.rerun()
    st.markdown('<div style="direction:ltr;text-align:center;color:rgba(255,255,255,0.3);font-size:10px;line-height:2;letter-spacing:1px;margin-top:8px;">نظام متعدد الوكلاء<br>هيئة الإحصاء العامة — 1447</div>', unsafe_allow_html=True)

mode = st.session_state.get("mode", "إدخال يدوي")

if "يدوي" in mode:
    st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] > div > [data-testid="stVerticalBlock"] {
        background: rgba(255,255,255,0.92) !important;
        backdrop-filter: blur(20px) !important;
        border-radius: 12px !important;
        padding: 20px 24px 28px 24px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.18) !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div > [data-testid="stVerticalBlock"] {
        background: transparent !important;
        backdrop-filter: none !important;
        border-radius: 0 !important;
        padding: 2px !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    error_placeholder = st.empty()
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<p class="section-title">معلومات الفرد</p>', unsafe_allow_html=True)
        age = st.number_input("العمر (سنة)", min_value=0, max_value=100, value=0)
        marital_status = st.selectbox("الحالة الاجتماعية", ["اختر الحالة", "أعزب", "متزوج", "مطلق", "أرمل"])
        education = st.selectbox("المؤهل التعليمي", ["اختر المؤهل", "ابتدائي", "متوسط", "ثانوي", "دبلوم", "بكالوريوس", "ماجستير", "دكتوراه"])
        occupation = st.text_input("المهنة", placeholder="اكتب المهنة")
        family_size = st.number_input("عدد أفراد الأسرة", min_value=0, max_value=20, value=0)

    with col2:
        st.markdown('<p class="section-title">معلومات السكن والدخل</p>', unsafe_allow_html=True)
        region = st.selectbox("المنطقة الإدارية", ["اختر المنطقة", "الرياض", "مكة", "جدة", "الشرقية", "المدينة", "نجران", "عسير", "الحدود الشمالية", "القصيم", "تبوك", "جازان", "حائل", "الباحة", "الجوف"])
        income = st.number_input("الدخل الشهري (ريال)", min_value=0, max_value=500000, value=0)
        actual_expenses = st.number_input("الإنفاق الشهري الفعلي (ريال)", min_value=0, max_value=200000, value=0)
        housing_type = st.selectbox("نوع الوحدة السكنية", ["اختر نوع الوحدة", "شقة", "فيلا", "منزل شعبي", "دور في فيلا", "دور في منزل شعبي", "أخرى"])
        electricity_bill = st.number_input("فاتورة الكهرباء الشهرية (ريال)", min_value=0, max_value=10000, value=0)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("بدء عملية التحقق والتحليل", type="primary", use_container_width=True):
        errors = []
        if age == 0: errors.append("العمر")
        if family_size == 0: errors.append("عدد أفراد الأسرة")
        if income == 0: errors.append("الدخل الشهري")
        if actual_expenses == 0: errors.append("الإنفاق الشهري الفعلي")
        if electricity_bill == 0: errors.append("فاتورة الكهرباء")
        if not occupation.strip(): errors.append("المهنة")
        if "اختر" in marital_status: errors.append("الحالة الاجتماعية")
        if "اختر" in education: errors.append("المؤهل التعليمي")
        if "اختر" in region: errors.append("المنطقة الإدارية")
        if "اختر" in housing_type: errors.append("نوع الوحدة السكنية")

        if errors:
            st.toast(f"⚠️ يرجى تعبئة: {', '.join(errors)}", icon="🚨")
            st.stop()
        else:
            record = record_to_dict(
                age, marital_status, education, occupation,
                family_size, region, income, actual_expenses,
                housing_type, electricity_bill
            )

            st.markdown("<br>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            status_container = st.empty()

            msg_placeholder = st.empty()

            # بدء التحليل في خلفية
            import concurrent.futures as cf2
            with cf2.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(analyze_record_parallel, record)

                # رسائل متسلسلة بالتوازي مع التحليل
                msg_placeholder.markdown('<div class="step-indicator">⏳ جاري تشغيل الوكيل الديموغرافي — تحليل بيانات الفرد والأسرة...</div>', unsafe_allow_html=True)
                progress_bar.progress(25)
                time.sleep(4.0)

                msg_placeholder.markdown('<div class="step-indicator">⏳ جاري تشغيل الوكيل المالي — مقارنة البيانات مع مؤشرات هيئة الإحصاء...</div>', unsafe_allow_html=True)
                progress_bar.progress(50)
                time.sleep(4.0)

                msg_placeholder.markdown('<div class="step-indicator">⏳ جاري تشغيل الوكيل القيادي — إصدار درجة الموثوقية النهائية...</div>', unsafe_allow_html=True)
                progress_bar.progress(75)

                result = future.result()

            demo_result = result['demographic']
            financial_result = result['financial']
            manager_result = result['manager']

            progress_bar.progress(100)
            time.sleep(0.3)
            msg_placeholder.empty()
            status_container.empty()

            log_analysis(st.session_state.current_user, "manual", 1)

            st.success("اكتملت عملية التحليل بنجاح")
            st.markdown("<br>", unsafe_allow_html=True)

            trust_score = manager_result.get('trust_score', 0)
            status = manager_result.get('status', '')

            if trust_score >= 75:
                score_color = "#3ecfa0"
                status_icon = "✓"
            elif trust_score >= 50:
                score_color = "#F2A365"
                status_icon = "⚠"
            else:
                score_color = "#e05c5c"
                status_icon = "✗"

            col_score, col_status = st.columns(2, gap="large")

            with col_score:
                st.markdown(f"""
                <div class="result-score-card">
                    <div class="score-number" style="color:{score_color};">{trust_score}%</div>
                    <div class="score-label">درجة الموثوقية النهائية</div>
                </div>
                """, unsafe_allow_html=True)

            with col_status:
                st.markdown(f"""
                <div class="result-status-card">
                    <div class="status-icon-large" style="color:{score_color};">{status_icon}</div>
                    <div class="status-text">{status}</div>
                    <div class="status-sub">الحالة النهائية للسجل</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<p class="agents-title">تفاصيل تحليل الوكلاء</p>', unsafe_allow_html=True)

            col_d, col_f, col_m = st.columns(3, gap="medium")

            with col_d:
                d_status = demo_result.get('status', '')
                d_color = "#3ecfa0" if "منطقي" in d_status else "#F2A365"
                st.markdown(f"""
                <div class="agent-result-card">
                    <div class="agent-header">
                        <div class="agent-dot" style="background:{d_color};"></div>
                        <span class="agent-name">الوكيل الديموغرافي</span>
                    </div>
                    <div class="agent-field"><span class="agent-field-label">الحالة</span><span class="agent-field-value">{d_status}</span></div>
                    <div class="agent-field"><span class="agent-field-label">الدرجة</span><span class="agent-field-value">{demo_result.get('score', 0)} / 100</span></div>
                    <div style="padding-top:12px; border-top:1px solid #f0f4f3;">
                        <div style="color:#8a9c9a; font-size:12px; margin-bottom:6px;">الملاحظات</div>
                        <div style="color:#1a1a1a; font-size:13px; line-height:1.7;">{demo_result.get('notes', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                for issue in demo_result.get('issues', []):
                    st.markdown(f'<div class="issue-badge">{issue}</div>', unsafe_allow_html=True)

            with col_f:
                f_status = financial_result.get('status', '')
                f_color = "#3ecfa0" if "منطقي" in f_status else "#F2A365"
                st.markdown(f"""
                <div class="agent-result-card">
                    <div class="agent-header">
                        <div class="agent-dot" style="background:{f_color};"></div>
                        <span class="agent-name">الوكيل المالي</span>
                    </div>
                    <div class="agent-field"><span class="agent-field-label">الحالة</span><span class="agent-field-value">{f_status}</span></div>
                    <div class="agent-field"><span class="agent-field-label">الدرجة</span><span class="agent-field-value">{financial_result.get('score', 0)} / 100</span></div>
                    <div style="padding-top:12px; border-top:1px solid #f0f4f3;">
                        <div style="color:#8a9c9a; font-size:12px; margin-bottom:6px;">الملاحظات</div>
                        <div style="color:#1a1a1a; font-size:13px; line-height:1.7;">{financial_result.get('notes', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                for issue in financial_result.get('issues', []):
                    st.markdown(f'<div class="issue-badge">{issue}</div>', unsafe_allow_html=True)

            with col_m:
                st.markdown(f"""
                <div class="agent-result-card">
                    <div class="agent-header">
                        <div class="agent-dot" style="background:#1A6B52;"></div>
                        <span class="agent-name">الوكيل القيادي</span>
                    </div>
                    <div class="agent-field"><span class="agent-field-label">الحالة</span><span class="agent-field-value">{status}</span></div>
                    <div class="agent-field" style="border:none;"><span class="agent-field-label">درجة الموثوقية</span><span class="agent-field-value" style="color:{score_color}; font-size:20px; font-weight:700;">{trust_score}%</span></div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f'<div class="recommendation-box">{manager_result.get("recommendation", "")}</div>', unsafe_allow_html=True)

            st.markdown('<p class="agents-title">التحليل البياني</p>', unsafe_allow_html=True)

            col_gauge, col_bar = st.columns(2, gap="large")

            with col_gauge:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=trust_score,
                    title={'text': "درجة الموثوقية", 'font': {'size': 16, 'family': 'Tajawal'}},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': score_color},
                        'steps': [
                            {'range': [0, 50], 'color': '#ffe5e5'},
                            {'range': [50, 75], 'color': '#fff3e0'},
                            {'range': [75, 100], 'color': '#e5f5ee'},
                        ],
                        'threshold': {
                            'line': {'color': score_color, 'width': 4},
                            'thickness': 0.75,
                            'value': trust_score
                        }
                    }
                ))
                fig_gauge.update_layout(
                    height=280,
                    margin=dict(t=40, b=0, l=20, r=20),
                    paper_bgcolor='rgba(255,255,255,0.92)',
                    font={'family': 'Tajawal'},
                    dragmode=False
                )
                st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

            with col_bar:
                agents_names = ['الوكيل الديموغرافي', 'الوكيل المالي', 'الوكيل القيادي']
                agents_scores = [
                    demo_result.get('score', 0),
                    financial_result.get('score', 0),
                    trust_score
                ]
                bar_colors = []
                for s in agents_scores:
                    if s >= 75:
                        bar_colors.append('#3ecfa0')
                    elif s >= 50:
                        bar_colors.append('#F2A365')
                    else:
                        bar_colors.append('#e05c5c')

                fig_bar = go.Figure(go.Bar(
                    x=agents_scores,
                    y=agents_names,
                    orientation='h',
                    marker_color=bar_colors,
                    text=[f'{s}%' for s in agents_scores],
                    textposition='outside'
                ))
                fig_bar.update_layout(
                    title={'text': 'مقارنة درجات الوكلاء', 'font': {'size': 16, 'family': 'Tajawal'}},
                    xaxis={'range': [0, 110], 'title': 'الدرجة'},
                    height=280,
                    margin=dict(t=40, b=20, l=20, r=40),
                    paper_bgcolor='rgba(255,255,255,0.92)',
                    plot_bgcolor='rgba(255,255,255,0)',
                    font={'family': 'Tajawal'},
                    dragmode=False
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

elif "CSV" in mode:
    st.markdown('<p class="section-title">رفع ملف البيانات للتحليل الجماعي</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("اختر ملف CSV", type=['csv'])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.success(f"تم رفع الملف بنجاح — {len(df)} سجل")
        st.dataframe(df.head())

        if st.button("بدء التحليل الجماعي", type="primary", use_container_width=True):
            try:
                records = csv_to_records(df)
                total_records = len(records)
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.markdown('<div class="step-indicator">جاري تشغيل الوكيل الديموغرافي والمالي والقيادي على جميع السجلات...</div>', unsafe_allow_html=True)
                results = [None] * total_records

                BATCH_SIZE = 5

                def process_record(args):
                    idx, record = args
                    return idx, analyze_record_parallel(record)

                completed = 0
                with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                    futures = {executor.submit(process_record, (i, record)): i for i, record in enumerate(records)}
                    for future in concurrent.futures.as_completed(futures):
                        idx, result = future.result()
                        results[idx] = {
                            'record_index': idx + 1,
                            'original_record': records[idx],
                            'demographic': result['demographic'],
                            'financial': result['financial'],
                            'manager': result['manager']
                        }
                        completed += 1
                        progress_bar.progress(completed / total_records)

                status_text.empty()
                log_analysis(st.session_state.current_user, "batch", len(results))
                st.success(f"اكتمل تحليل {len(results)} سجل بنجاح")

                total = len(results)
                trusted = sum(1 for r in results if r['manager'].get('trust_score', 0) >= 75)
                review = sum(1 for r in results if 50 <= r['manager'].get('trust_score', 0) < 75)
                rejected = sum(1 for r in results if r['manager'].get('trust_score', 0) < 50)

                st.markdown('<p class="agents-title">إحصائيات التحليل الإجمالي</p>', unsafe_allow_html=True)

                col_t, col_tr, col_rv, col_rj = st.columns(4, gap="medium")
                with col_t:
                    st.markdown(f"""
                    <div class="result-score-card" style="padding:20px;">
                        <div class="score-number" style="color:#1A6B52;font-size:48px;">{total}</div>
                        <div class="score-label">إجمالي السجلات</div>
                    </div>""", unsafe_allow_html=True)
                with col_tr:
                    st.markdown(f"""
                    <div class="result-score-card" style="padding:20px;">
                        <div class="score-number" style="color:#3ecfa0;font-size:48px;">{trusted}</div>
                        <div class="score-label">سجلات موثوقة</div>
                    </div>""", unsafe_allow_html=True)
                with col_rv:
                    st.markdown(f"""
                    <div class="result-score-card" style="padding:20px;">
                        <div class="score-number" style="color:#F2A365;font-size:48px;">{review}</div>
                        <div class="score-label">تحتاج مراجعة</div>
                    </div>""", unsafe_allow_html=True)
                with col_rj:
                    st.markdown(f"""
                    <div class="result-score-card" style="padding:20px;">
                        <div class="score-number" style="color:#e05c5c;font-size:48px;">{rejected}</div>
                        <div class="score-label">مرفوضة</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown('<p class="agents-title">التحليل البياني الإجمالي</p>', unsafe_allow_html=True)

                col_pie, col_avg = st.columns(2, gap="large")

                with col_pie:
                    fig_pie = go.Figure(go.Pie(
                        labels=['موثوقة', 'تحتاج مراجعة', 'مرفوضة'],
                        values=[trusted, review, rejected],
                        marker_colors=['#3ecfa0', '#F2A365', '#e05c5c'],
                        hole=0.4,
                        textfont={'family': 'Tajawal', 'size': 13}
                    ))
                    fig_pie.update_layout(
                        title={'text': 'توزيع نتائج التحليل', 'font': {'size': 16, 'family': 'Tajawal'}},
                        height=300,
                        margin=dict(t=40, b=0, l=20, r=20),
                        paper_bgcolor='rgba(255,255,255,0.92)',
                        font={'family': 'Tajawal'},
                        showlegend=True
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

                with col_avg:
                    avg_demo = sum(r['demographic'].get('score', 0) for r in results) / total if total > 0 else 0
                    avg_fin = sum(r['financial'].get('score', 0) for r in results) / total if total > 0 else 0
                    avg_trust = sum(r['manager'].get('trust_score', 0) for r in results) / total if total > 0 else 0

                    avg_scores = [round(avg_demo), round(avg_fin), round(avg_trust)]
                    avg_colors = ['#3ecfa0' if s >= 75 else '#F2A365' if s >= 50 else '#e05c5c' for s in avg_scores]

                    fig_avg = go.Figure(go.Bar(
                        x=avg_scores,
                        y=['الوكيل الديموغرافي', 'الوكيل المالي', 'الوكيل القيادي'],
                        orientation='h',
                        marker_color=avg_colors,
                        text=[f'{s}%' for s in avg_scores],
                        textposition='outside'
                    ))
                    fig_avg.update_layout(
                        title={'text': 'متوسط درجات الوكلاء', 'font': {'size': 16, 'family': 'Tajawal'}},
                        xaxis={'range': [0, 110], 'title': 'الدرجة'},
                        height=300,
                        margin=dict(t=40, b=20, l=20, r=40),
                        paper_bgcolor='rgba(255,255,255,0.92)',
                        plot_bgcolor='rgba(255,255,255,0)',
                        font={'family': 'Tajawal'},
                        dragmode=False
                    )
                    st.plotly_chart(fig_avg, use_container_width=True, config={'displayModeBar': False})

                filename = export_to_excel(results)
                with open(filename, 'rb') as f:
                    st.download_button(label="تحميل تقرير Excel", data=f.read(), file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except ValueError as e:
                st.error(f"خطأ في الملف: {str(e)}")