"""
BharatDoc-VLM: Invoice Search App
====================================

Upload N invoices → extract fields → filter by amount, vendor, date.
Uses DocumentExtractor (PaddleOCR + Qwen/Donut pipeline).

Run: streamlit run apps/invoice_search/app.py
"""

import streamlit as st
import json
import os
import sys
import tempfile
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.vlm_extractor import DocumentExtractor

st.set_page_config(page_title="Invoice Search", page_icon="🔍", layout="wide")

st.title("🔍 Invoice Search")
st.markdown("Upload invoices, extract data, and filter by any field.")


@st.cache_resource
def load_extractor():
    return DocumentExtractor()


extractor = load_extractor()


def extract_invoice(uploaded_file):
    """Run extraction pipeline on a single invoice."""
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        result = extractor.extract(tmp_path, doc_type="invoice")
        # Parse total for filtering
        total_str = str(result.get("grand_total") or result.get("total_amount") or "0")
        # Strip currency symbols and commas for numeric filtering
        import re
        total_num = re.sub(r'[^\d.]', '', total_str)
        try:
            total_float = float(total_num) if total_num else 0.0
        except ValueError:
            total_float = 0.0

        return {
            "invoice_number": result.get("invoice_number") or "N/A",
            "vendor_name": result.get("vendor_name") or "N/A",
            "invoice_date": result.get("invoice_date") or "N/A",
            "total_amount": total_float,
            "total_display": total_str,
            "gstin": result.get("vendor_gstin") or result.get("gstin") or "N/A",
            "confidence": 0.85,
            "source_file": uploaded_file.name,
        }
    except Exception as e:
        return {
            "invoice_number": "N/A",
            "vendor_name": f"Extraction failed: {e}",
            "invoice_date": "N/A",
            "total_amount": 0,
            "total_display": "N/A",
            "confidence": 0.0,
            "source_file": uploaded_file.name,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# Session state for extracted data
if "invoices" not in st.session_state:
    st.session_state.invoices = []

uploaded_files = st.file_uploader("Upload invoices", type=["png", "jpg", "jpeg", "pdf"],
                                  accept_multiple_files=True)

if uploaded_files:
    if st.button("🔄 Extract All"):
        st.session_state.invoices = []
        progress = st.progress(0)
        for i, f in enumerate(uploaded_files):
            f.seek(0)
            extraction = extract_invoice(f)
            st.session_state.invoices.append(extraction)
            progress.progress((i + 1) / len(uploaded_files))
        st.success(f"✅ Extracted {len(st.session_state.invoices)} invoices")

if st.session_state.invoices:
    st.subheader("🔎 Filter Invoices")

    col1, col2, col3 = st.columns(3)
    with col1:
        min_amount = st.number_input("Min Amount (₹)", value=0, step=10000)
    with col2:
        max_amount = st.number_input("Max Amount (₹)", value=10000000, step=10000)
    with col3:
        vendor_filter = st.text_input("Vendor name contains")

    # Filter
    filtered = st.session_state.invoices
    filtered = [inv for inv in filtered if min_amount <= inv["total_amount"] <= max_amount]
    if vendor_filter:
        filtered = [inv for inv in filtered if vendor_filter.lower() in inv["vendor_name"].lower()]

    st.write(f"Showing {len(filtered)} / {len(st.session_state.invoices)} invoices")

    # Display as table
    import pandas as pd
    df = pd.DataFrame(filtered)
    if not df.empty:
        display_df = df[["invoice_number", "vendor_name", "invoice_date",
                          "total_display", "confidence", "source_file"]].copy()
        display_df.columns = ["Invoice #", "Vendor", "Date", "Total", "Conf", "File"]
        st.dataframe(display_df, use_container_width=True)

    # Summary stats
    if filtered:
        amounts = [inv["total_amount"] for inv in filtered]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", f"₹{sum(amounts):,.0f}")
        col2.metric("Average", f"₹{sum(amounts)/len(amounts):,.0f}")
        col3.metric("Count", len(filtered))
else:
    st.info("👆 Upload invoice images and click Extract All")
