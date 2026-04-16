import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import re

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")
st.subheader("Dual-View Analysis")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    # Manual Key Entry
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    
    if st.button("Clear All Data"):
        st.session_state.analysis_results = []
        st.rerun()

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        return ""

def get_gemini_score(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        # FIXED: Changed from 'gemini-2.5' to the stable 'gemini-1.5-flash'
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        Analyze Resume vs JD. Return STRICTLY in this format: 
        Score: [number] | Review: [text] | Guidance: [text]
        
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Memory Management ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- Input Section ---
# Added unique 'key' to prevent Duplicate ID errors
job_description = st.text_area("📋 Paste Job Description (JD):", height=150, key="jd_input_box")
uploaded_files = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True, key="file_uploader_box")

# --- Processing Section ---
if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Please provide API Key, JD, and Resumes.")
    else:
        temp_results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            with st.spinner(f"Analyzing {file.name}..."):
                text = extract_text_from_pdf(file)
                analysis = get_gemini_score(text, job_description, api_key)
                
                try:
                    # Improved parsing to find the number even if the AI adds words
                    parts = analysis.split("|")
                    score_match = re.search(r'\d+', parts[0])
                    score = int(score_match.group()) if score_match else 0
                    
                    temp_results.append({
                        "Name": file.name,
                        "Score": score,
                        "Recruiter_Notes": parts[1].replace("Review:", "").strip() if len(parts) > 1 else "No review provided",
                        "Applicant_Notes": parts[2].replace("Guidance:", "").strip() if len(parts) > 2 else "No guidance provided"
                    })
                except:
                    temp_results.append({"Name": file.name, "Score": 0, "Recruiter_Notes": "Parsing error", "Applicant_Notes": "N/A"})
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.session_state.analysis_results = temp_results

# --- Display Results ---
if st.session_state.analysis_results:
    st.markdown("---")
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    for index, row in df.iterrows():
        # Added 'key' to the expander and buttons to prevent DuplicateElementId errors
        with st.expander(f"📊 {row['Score']}% — {row['Name']}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🏢 Company Internal Review")
                st.warning(row["Recruiter_Notes"])
            with c2:
                st.markdown("#### 🎓 Applicant Guidance")
                st.info(row["Applicant_Notes"])
            
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                # Keys are now unique using the index
                if st.button("Shortlist", key=f"sl_btn_{index}"):
                    st.success(f"Shortlisted {row['Name']}!")
            with col_btn2:
                if st.button("Send Feedback", key=f"fb_btn_{index}"):
                    st.info(f"Feedback prepared for {row['Name']}")
