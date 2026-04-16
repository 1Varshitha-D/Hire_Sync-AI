import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import re

# --- 1. SETUP ---
st.set_page_config(page_title="HireSync AI", layout="wide")
st.title("🎯 HireSync AI")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    if st.button("Clear Results"):
        st.session_state.analysis_results = []
        st.rerun()

# --- 3. LOGIC ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

def extract_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def get_analysis(text, jd, key):
    try:
        genai.configure(api_key=key)
        # Using 1.5-flash because it is the most stable version right now
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Score: 0-100 | Review | Guidance. JD: {jd} Resume: {text}"
        return model.generate_content(prompt).text
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- 4. INPUTS ---
jd = st.text_area("📋 Job Description:", height=150, key="jd_box")
files = st.file_uploader("📂 Resumes:", type="pdf", accept_multiple_files=True, key="file_box")

# --- 5. RUN ---
if st.button("🚀 Analyze"):
    if not api_key or not jd or not files:
        st.error("Missing Info")
    else:
        results = []
        bar = st.progress(0)
        for i, f in enumerate(files):
            raw = get_analysis(extract_text(f), jd, api_key)
            try:
                parts = raw.split("|")
                # Grab just the number for the score
                num = int(re.search(r'\d+', parts[0]).group()) if parts else 0
                results.append({
                    "name": f.name, "score": num,
                    "notes": parts[1] if len(parts) > 1 else "Done",
                    "tips": parts[2] if len(parts) > 2 else "N/A"
                })
            except: pass
            bar.progress((i + 1) / len(files))
        st.session_state.analysis_results = results

# --- 6. DISPLAY ---
if st.session_state.analysis_results:
    for i, res in enumerate(st.session_state.analysis_results):
        with st.expander(f"{res['score']}% - {res['name']}"):
            st.write(f"**Review:** {res['notes']}")
            st.write(f"**Tips:** {res['tips']}")
            # Unique keys for buttons prevent the Duplicate ID error
            if st.button(f"Shortlist {res['name']}", key=f"sl_{i}"):
                st.success("Saved!")
