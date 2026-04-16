import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import re

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    
    st.markdown("---")
    if st.button("🔄 Clear All Results"):
        st.session_state.analysis_results = []
        st.rerun()

# --- Memory Management ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except:
        return ""

def get_gemini_analysis(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        Compare Resume to JD. 
        Format: Score: [0-100] | Review: [text] | Guidance: [text]
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Main Input Section ---
# I added a unique 'key' here to stop the Duplicate ID error
jd_input = st.text_area("📋 Paste Job Description (JD):", height=150, key="main_jd_box")
files_input = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True, key="resume_uploader")

if st.button("🚀 Run Analysis"):
    if not api_key or not jd_input or not files_input:
        st.error("Please provide API Key, JD, and Resumes.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(files_input):
            text = extract_text_from_pdf(file)
            analysis = get_gemini_analysis(text, jd_input, api_key)
            
            try:
                score_match = re.search(r'\d+', analysis)
                score = int(score_match.group()) if score_match else 0
                parts = analysis.split("|")
                results.append({
                    "Name": file.name,
                    "Score": score,
                    "Review": parts[1].strip() if len(parts) > 1 else "No review",
                    "Guidance": parts[2].strip() if len(parts) > 2 else "No guidance"
                })
            except:
                results.append({"Name": file.name, "Score": 0, "Review": "Error", "Guidance": "N/A"})
            
            progress_bar.progress((i + 1) / len(files_input))
        st.session_state.analysis_results = results

# --- Display Results ---
if st.session_state.analysis_results:
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    for index, row in df.iterrows():
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            st.warning(f"**Review:** {row['Review']}")
            st.info(f"**Guidance:** {row['Guidance']}")
