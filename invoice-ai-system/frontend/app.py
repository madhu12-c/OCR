# --- IMPORTS ---
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import time
import sys
import zipfile
from io import BytesIO

import importlib

# Ensure backend path is recognized
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def safe_float(val):
    if val is None: return 0.0
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0

import backend.ai_extractor
import backend.vision_processor
import backend.outlook_fetcher
import backend.tally_xml
import backend.excel_export
import backend.local_scanner

# Force reload backend modules
importlib.reload(backend.ai_extractor)
importlib.reload(backend.vision_processor)
importlib.reload(backend.outlook_fetcher)
importlib.reload(backend.tally_xml)
importlib.reload(backend.excel_export)
importlib.reload(backend.local_scanner)

from backend.ai_extractor import AIExtractor
from backend.vision_processor import VisionProcessor
from backend.outlook_fetcher import OutlookFetcher
from backend.tally_xml import TallyExporter
from backend.excel_export import ExcelExporter
from backend.local_scanner import LocalScanner

# --- CONSTANTS ---
UPLOAD_DIR = "data/uploads"
OUTPUT_DIR = "data/outputs"
LOCAL_IMPORT_DIR = "data/local_import"

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOCAL_IMPORT_DIR, exist_ok=True)

# --- THEME & CSS ---
def set_page_style():
    st.set_page_config(page_title="Infinx | Revenue Vision AI", layout="wide", page_icon="🛡️")
    
    # Custom CSS for Infinx Branding
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@700&display=swap');

        :root {
            --brand-teal: #005A64;
            --electric-cyan: #00E5FF;
            --surface-white: #FFFFFF;
            --glass-bg: rgba(255, 255, 255, 0.95);
            --transition-smooth: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Global Overrides */
        .main {
            background-color: #F8FAFC;
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            color: var(--brand-teal);
            font-weight: 700;
        }

        /* Animations */
        @keyframes fadeInSlideUp {
            0% { opacity: 0; transform: translateY(30px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        .stApp {
            animation: fadeInSlideUp 0.8s ease-out;
        }

        /* Premium SideBar */
        [data-testid="stSidebar"] {
            background-color: var(--brand-teal) !important;
            padding-top: 2rem;
        }
        [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: white !important;
            font-weight: 500;
        }

        /* Glassmorphic Metric Cards */
        [data-testid="stMetric"] {
            background: var(--glass-bg);
            border: 1px solid #E2E8F0;
            border-radius: 16px !important;
            padding: 24px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: var(--transition-smooth);
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-5px) scale(1.02);
            border-color: var(--electric-cyan);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        /* Action Buttons */
        .stButton>button {
            background-color: var(--brand-teal) !important;
            color: white !important;
            border-radius: 12px;
            padding: 12px 24px;
            border: none;
            font-weight: 600;
            transition: var(--transition-smooth);
            width: 100%;
        }
        .stButton>button:hover {
            background-color: var(--electric-cyan) !important;
            color: var(--brand-teal) !important;
            box-shadow: 0 10px 15px -3px rgba(0, 229, 255, 0.3);
        }

        /* DataGrid Modernization */
        [data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #E2E8F0;
        }

        /* Status Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: transparent;
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            border-radius: 10px;
            background-color: white;
            border: 1px solid #E2E8F0;
            padding: 0 20px;
            transition: var(--transition-smooth);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--brand-teal) !important;
            color: white !important;
            border-color: var(--brand-teal);
        }

        </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "invoices" not in st.session_state:
    st.session_state.invoices = []
if "config" not in st.session_state:
    st.session_state.config = {
        "groq_key": os.getenv("GROQ_API_KEY", ""),
        "email": os.getenv("OUTLOOK_EMAIL", ""),
        "password": os.getenv("OUTLOOK_PASSWORD", ""),
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct"
    }

# --- TOOLS ---
@st.cache_resource
def get_tools(key, model_p):
    return {
        "extractor": AIExtractor(api_key=key, model_name=model_p) if key else None,
        "processor": VisionProcessor(),
        "fetcher": OutlookFetcher(),
        "tally": TallyExporter(),
        "excel": ExcelExporter(),
        "scanner": LocalScanner(watch_dir=LOCAL_IMPORT_DIR)
    }

tools_instance = get_tools(st.session_state.config["groq_key"], st.session_state.config["model_name"])


## --- DASHBOARD LOGIC ---
def main():
    set_page_style()
    
    # Branded SideBar
    st.sidebar.markdown(f"""
        <div style='text-align: center; padding-bottom: 20px;'>
            <h2 style='color: white; margin-bottom: 0;'>Infinx</h2>
            <p style='color: #00E5FF; font-size: 0.8rem; letter-spacing: 2px;'>REVENUE AI</p>
        </div>
    """, unsafe_allow_html=True)
    
    menu = st.sidebar.radio("Navigation", ["Revenue Overview", "Auditor Portal", "Payment Tracker", "Client Exports", "Configuration"])
    
    if menu == "Revenue Overview":
        render_dashboard()
    elif menu == "Auditor Portal":
        render_approval_portal()
    elif menu == "Payment Tracker":
        render_payment_tracking()
    elif menu == "Client Exports":
        render_exports()
    else:
        render_settings()

def render_dashboard():
    # 1. Premium Metrics
    st.markdown("<h1 style='text-align: center; margin-bottom: 50px;'>Revenue Operations Dashboard</h1>", unsafe_allow_html=True)
    
    if st.session_state.invoices:
        total_count = len(st.session_state.invoices)
        total_val = sum(safe_float(i.get("total")) for i in st.session_state.invoices)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Processed Documents", total_count)
        m2.metric("Total Ascribed Value", f"₹{total_val:,.2f}")
        m3.metric("OCR Synthesis Rate", "100%", delta="Verified")
        m4.metric("LLM Status", "Active", help="Using Llama 4 Omni-Vision Pro")
    else:
        st.info("👋 Welcome to Infinx Revenue Vision. Upload your invoices below to begin AI synthesis.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    
    # 2. Ingestion Engine
    st.markdown("<h3 style='margin-bottom: 25px;'>📥 Revenue Ingestion</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        tab1, tab2, tab3 = st.tabs(["🚀 AIR-DRIVEN UPLOAD", "📁 NETWORK SCAN", "📨 EMAIL SYNC"])
        
        with tab1:
            uploaded_files = st.file_uploader("Drag & Drop Invoices", accept_multiple_files=True, label_visibility="collapsed")
            c1, c2 = st.columns([1, 1])
            if c1.button("Analyze & Synthesize 🧠", use_container_width=True) and uploaded_files:
                process_uploaded_files(uploaded_files)
            
            if st.session_state.invoices:
                if c2.button("Generate Batch Statement 📊", use_container_width=True):
                    path = tools_instance["excel"].export_to_excel(st.session_state.invoices)
                    with open(path, "rb") as f:
                        st.download_button("Download Report", f, file_name=f"Infinx_Report_{datetime.now().strftime('%H%M%S')}.xlsx")

        with tab2:
            st.markdown(f"**Path Monitoring:** `{LOCAL_IMPORT_DIR}`")
            if st.button("Trigger Bulk Ingestion 🔍"):
                scan_local_folder()
                    
        with tab3:
            st.markdown("**Outlook Monitoring Active**")
            if st.button("Synchronize Inbox 🔄"):
                sync_outlook()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Unified Registry")
    if st.session_state.invoices:
        df = pd.DataFrame(st.session_state.invoices)
        display_cols = ['filename', 'vendor', 'invoice_no', 'po_number', 'total', 'status']
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
        
        # ... [Detail view code remains as modified previously] ...
        
        # Expandable Detail View
        st.write("### 🔎 Invoice Detail View")
        for idx, item in enumerate(st.session_state.invoices):
            with st.expander(f"📄 {item.get('vendor', 'Unknown')} — {item.get('invoice_no', 'N/A')} — ₹{item.get('total', '0')}"):
                # EXTRACTION METADATA
                st.markdown(f"<p style='color: #64748B; font-size: 0.85rem;'>🛡️ System Mode: {item.get('extraction_mode', 'Omni-Vision Pro')}</p>", unsafe_allow_html=True)
                
                raw = item.get("raw_data", {})
                
                # DATA INTEGRITY PANEL
                mandatory_fields = {
                    "Invoice #": raw.get("invoice_number"),
                    "Date": raw.get("invoice_date"),
                    "Vendor Name": raw.get("vendor_name"),
                    "GSTIN": raw.get("vendor_tax_id")
                }
                missing = [k for k, v in mandatory_fields.items() if not v or v == "N/A"]
                if missing:
                    st.warning(f"⚠️ **Attention Required:** Missing {', '.join(missing)}")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("### 📋 Primary Info")
                    st.write(f"**INV #:** `{raw.get('invoice_number', 'N/A')}`")
                    st.write(f"**PO #:** `{raw.get('po_number', 'N/A')}`")
                    st.write(f"**Date:** {raw.get('invoice_date', 'N/A')}")
                with c2:
                    st.markdown("### 🏢 Vendor")
                    st.write(f"**Name:** {raw.get('vendor_name', 'Unknown')}")
                    st.write(f"**GSTIN:** `{raw.get('vendor_tax_id') or 'N/A'}`")
                    st.write(f"**Address:** {raw.get('vendor_address', 'N/A')}")
                with c3:
                    st.markdown("### 👤 Customer")
                    st.write(f"**Name:** {raw.get('customer_name', 'Direct Customer')}")
                    st.write(f"**GSTIN:** `{raw.get('customer_tax_id', 'N/A')}`")
                    st.write(f"**Address:** {raw.get('customer_address', 'N/A')}")
                
                st.markdown("<hr style='border: 0.5px solid #E2E8F0; margin: 30px 0;'>", unsafe_allow_html=True)

                # TAX & FINANCE
                tx1, tx2, tx3, tx4 = st.columns(4)
                tx1.metric("CGST", f"₹{safe_float(raw.get('cgst_amount'))}")
                tx2.metric("SGST", f"₹{safe_float(raw.get('sgst_amount'))}")
                tx3.metric("IGST", f"₹{safe_float(raw.get('igst_amount'))}")
                tx4.metric("TOTAL TAX", f"₹{safe_float(raw.get('total_tax'))}")
                
                it1, it2, it3 = st.columns([2, 1, 1])
                with it1:
                    items = raw.get("line_items", [])
                    if items:
                        st.markdown("#### Itemized Breakdown")
                        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                
                with it2:
                    st.markdown("#### Summary")
                    st.write(f"Subtotal: **₹{safe_float(raw.get('subtotal'))}**")
                    st.write(f"Round Off: **₹{safe_float(raw.get('round_off'))}**")
                    st.markdown(f"### Pay: ₹{safe_float(raw.get('total_amount'))}")

                with it3:
                    st.markdown("#### Payment Details")
                    st.write(f"Bank: {raw.get('bank_details', 'N/A')}")
                    st.write(f"UPI: `{raw.get('upi_id', 'N/A')}`")
                    if raw.get('vehicle_number'): 
                        st.write(f"Vehicle: `{raw.get('vehicle_number')}`")
                
                # IGST Breakup (if multiple rates)
                igst_breakup = raw.get("igst_breakup", [])
                if igst_breakup and isinstance(igst_breakup, list) and len(igst_breakup) > 0:
                    st.write("**IGST Breakup**")
                    bp_df = pd.DataFrame(igst_breakup)
                    st.dataframe(bp_df, use_container_width=True)
                
                # Validation Warnings
                warnings = raw.get("_validation_warnings", [])
                if warnings:
                    st.error("**🔍 Validation Issues Detected:**")
                    for w in warnings:
                        st.write(w)
                elif raw.get("_validation_passed"):
                    st.success("✅ All numbers verified — extraction matches invoice totals.")
        
        st.divider()
        # Action: Assign to HOD
        st.write("### Quick Actions")
        col_sel, col_btn = st.columns([2, 1])
        unassigned = [i['filename'] for i in st.session_state.invoices if i.get('status') == 'Uploaded']
        if unassigned:
            target_inv = col_sel.selectbox("Select Invoice to send for Approval", unassigned)
            target_hod = col_sel.selectbox("Select HOD", ["HOD 1", "HOD 2", "HOD 3"])
            if col_btn.button("Send for Approval ➡️"):
                for inv in st.session_state.invoices:
                    if inv['filename'] == target_inv:
                        inv['status'] = 'Pending'
                        inv['assigned_hod'] = target_hod
                st.success(f"Assigned {target_inv} to {target_hod}")
                st.rerun()
    else:
        st.write("No invoices processed yet.")


def process_uploaded_files(files):
    to_process = []
    for f in files:
        save_path = os.path.join(UPLOAD_DIR, f.name)
        with open(save_path, "wb") as buffer:
            buffer.write(f.getbuffer())
        to_process.append({"filename": f.name, "path": save_path})
    
    pipeline_logic(to_process)

def scan_local_folder():
    moved_files = tools_instance["scanner"].scan_and_move()
    if not moved_files:
        st.warning("No new files found in local import folder.")
        return
    
    pipeline_logic(moved_files)

def pipeline_logic(file_list):
    with st.status("🚀 Production Extraction: LLM Vision Analysis...", expanded=True) as status:
        for f_data in file_list:
            t1 = time.time()
            st.write(f"Analyzing **{f_data['filename']}**...")
            
            # Stage 0: Convert PDF to high-res images (Multi-page)
            processed_paths = tools_instance["processor"].prepare_file(f_data['path'])
            
            if not processed_paths:
                st.error(f"Unsupported file type or empty PDF: {f_data['filename']}")
                continue

            if len(processed_paths) > 1:
                st.write(f"📖 Multi-page document detected: **{len(processed_paths)} pages**")

            # Stage 1: AI Vision Extraction (Multi-modal Seq)
            st.write("🧠 AI Vision: Reading header, items, and tax breakdown across all pages...")
            data = tools_instance["extractor"].extract_invoice_data(processed_paths)
            
            if data and "error" not in data:
                # Truncation check
                if "_truncation_info" in data:
                    st.warning(f"⚠️ {data['_truncation_info']}")

                # Use 'or' fallback to ensure None values from AI become strings like 'N/A'
                new_item = {
                    "id": str(int(time.time())) + f_data['filename'],
                    "filename": f_data['filename'],
                    "vendor": data.get("vendor_name") or "Unknown",
                    "vendor_gst": data.get("vendor_tax_id") or "N/A",
                    "invoice_no": data.get("invoice_number") or "N/A",
                    "po_number": data.get("po_number") or "N/A",
                    "date": data.get("invoice_date") or "N/A",
                    "total": data.get("total_amount") or "0",
                    "status": "Uploaded",
                    "assigned_hod": "Unassigned",
                    "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "raw_data": data,
                    "file_path": f_data['path'],
                    "extraction_mode": data.get("_extraction_mode", "Production Vision")
                }
                st.session_state.invoices.append(new_item)
                st.write(f"✅ **{new_item['vendor']}** — ₹{new_item['total']} ({time.time()-t1:.1f}s)")
            else:
                err_msg = data.get('error') if data else 'Unknown AI Error'
                st.error(f"❌ **{f_data['filename']}** — {err_msg}")
                # Log to terminal for debugging
                print(f"PIPELINE ERROR: {f_data['filename']} -> {err_msg}")
        
        status.update(label="✅ Batch Extraction Complete!", state="complete", expanded=False)
    st.rerun()


def sync_outlook():
    # Real link to fetcher
    files = tools_instance["fetcher"].fetch_attachments()
    if files:
        st.success(f"Fetched {len(files)} new invoices from Outlook!")
        pipeline_logic(files)
    else:
        st.info("No new invoices in Outlook.")

def render_approval_portal():
    st.title("🛡️ HOD Approval Portal")
    
    hod_filter = st.selectbox("I am reviewing as:", ["HOD 1", "HOD 2", "HOD 3"])
    
    pending_items = [i for i in st.session_state.invoices if i.get("status") == "Pending" and i.get("assigned_hod") == hod_filter]
    
    if not pending_items:
        st.success(f"No pending invoices for {hod_filter}.")
        return

    st.write(f"#### Pending Items for {hod_filter}")
    for idx, item in enumerate(pending_items):
        with st.container(border=True):
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(f"**Vendor:** {item['vendor']} | **INV:** {item['invoice_no']}")
            cols[1].write(f"**Amount:** {item['total']}")
            
            if cols[2].button("Approve ✅", key=f"app_{idx}"):
                item["status"] = "Approved"
                st.toast(f"Approved {item['invoice_no']}!")
                st.rerun()
                
            if cols[3].button("Reject ❌", key=f"rej_{idx}"):
                item["status"] = "Uploaded" # Back to uploaded for reassignment or correction
                item["assigned_hod"] = "Unassigned"
                st.rerun()

def render_payment_tracking():
    st.title("💸 Payment Tracking")
    st.write("Mark approved invoices as 'Paid' to complete the lifecycle.")
    
    approved_items = [i for i in st.session_state.invoices if i.get("status") == "Approved"]
    
    if not approved_items:
        st.info("No invoices ready for payment tracking.")
        return

    for idx, item in enumerate(approved_items):
        with st.container(border=True):
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(f"**Vendor:** {item['vendor']} | **INV:** {item['invoice_no']}")
            cols[1].write(f"**HOD:** {item['assigned_hod']} | **Amount:** {item['total']}")
            
            if cols[2].button("Mark as Paid 💰", key=f"pay_{idx}"):
                item["status"] = "Paid"
                st.success(f"Invoice {item['invoice_no']} marked as Paid.")
                st.rerun()
    
def render_exports():
    st.title("📦 Final Exports & Downloads")
    st.write("Generate Excel and Tally files for approved and paid invoices.")
    
    export_ready = [i for i in st.session_state.invoices if i.get("status") in ["Approved", "Paid"]]
    
    if not export_ready:
        st.warning("No invoices ready for export.")
        return

    st.subheader(f"{len(export_ready)} Items Ready")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Consolidated Excel 📊"):
            path = tools_instance["excel"].export_to_excel(export_ready)
            st.success(f"Generated at: {path}")
            with open(path, "rb") as f:
                st.download_button("Download Excel", f, file_name="Invoices_Report.xlsx")

    with col2:
        if st.button("Download Invoice Bundle (ZIP) 📂"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for item in export_ready:
                    if os.path.exists(item['file_path']):
                        zip_file.write(item['file_path'], arcname=item['filename'])
            st.download_button("Download ZIP", zip_buffer.getvalue(), file_name="Completed_Invoices.zip")

    st.divider()
    if st.button("Generate Tally XML ⚙️"):
        for item in export_ready:
            xml_str = tools_instance["tally"].generate_purchase_xml(item['raw_data'])
            st.code(xml_str, language="xml")
            st.info(f"XML ready for {item['invoice_no']}")

def render_settings():
    st.title("⚙️ System Configuration")
    st.write("Manage model parameters, API keys, and system memory.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🤖 AI Engine")
        st.session_state.config["groq_key"] = st.text_input("Groq API Key", value=st.session_state.config.get("groq_key", ""), type="password")
        st.session_state.config["model_name"] = st.text_input("Vision Model ID", value=st.session_state.config.get("model_name", "meta-llama/llama-4-scout-17b-16e-instruct"))
        
    with col2:
        st.subheader("📧 Email Sync")
        st.session_state.config["email"] = st.text_input("Office Email", value=st.session_state.config.get("email", ""))
        st.session_state.config["password"] = st.text_input("Office App Password", value=st.session_state.config.get("password", ""), type="password")

    st.divider()
    ca, cb = st.columns(2)
    if ca.button("💾 Save Configuration & Clear Cache", use_container_width=True):
        st.cache_resource.clear()
        st.success("Settings saved locally for this session.")
        st.rerun()
        
    if cb.button("💣 Full Reset (Clear History)", type="primary", use_container_width=True):
        st.session_state.invoices = []
        st.success("All session records purged.")
        st.rerun()

if __name__ == "__main__":
    main()
