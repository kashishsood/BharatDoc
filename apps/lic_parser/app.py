"""
BharatDoc-VLM: LIC Policy Parser App
=======================================

Upload an LIC policy document → extract + validate all fields.
Uses DocumentExtractor (PaddleOCR + Qwen/Donut pipeline).

Run: streamlit run apps/lic_parser/app.py
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
from schemas.models import LICPolicySchema, SchemaValidator

st.set_page_config(page_title="LIC Policy Parser", page_icon="🏛️", layout="wide")

st.title("🏛️ LIC Policy Parser")
st.markdown("Upload an LIC policy document to extract and validate all fields.")


@st.cache_resource
def load_extractor():
    return DocumentExtractor()


extractor = load_extractor()


def process_uploaded_file(uploaded_file):
    """Run extraction pipeline on uploaded LIC policy."""
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        result = extractor.extract(tmp_path, doc_type="lic_policy")
        # Filter internal keys for display
        return {k: v for k, v in result.items() if not str(k).startswith("_")}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


uploaded = st.file_uploader("Upload LIC Policy Image", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Uploaded Document")
        image = Image.open(uploaded).convert("RGB")
        st.image(image, use_container_width=True)

    with col2:
        st.subheader("📋 Extracted Fields")

        with st.spinner("Extracting fields..."):
            uploaded.seek(0)
            extraction = process_uploaded_file(uploaded)

        # Validate against schema
        validator = SchemaValidator()
        result = validator.validate("lic_policy", extraction)

        if result["valid"]:
            st.success("✅ All fields validated successfully")
            st.json(result["data"])
        else:
            st.warning("⚠️ Validation issues found")
            st.json(extraction)
            st.error("Validation Errors:")
            for err in result.get("errors", []):
                st.write(f"  • **{err['field']}**: {err['message']}")

    # Summary table
    st.subheader("📊 Policy Summary")
    summary = {
        "Policy Number": extraction.get("policy_number"),
        "Holder": extraction.get("holder_name"),
        "Plan": extraction.get("plan_name"),
        "Sum Assured": extraction.get("sum_assured"),
        "Premium": extraction.get("annual_premium"),
        "Maturity": extraction.get("maturity_date"),
        "Nominee": extraction.get("nominee"),
    }
    for k, v in summary.items():
        st.metric(label=k, value=str(v or "N/A"))
else:
    st.info("👆 Upload an LIC policy image to get started")
    st.markdown("### Supported Extractions\n- Policy number, holder name, plan details\n"
                "- Sum assured, premium amount and frequency\n- Maturity date, nominee details\n"
                "- Rider benefits")
