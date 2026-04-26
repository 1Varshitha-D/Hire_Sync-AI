import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import time  # NEW: Needed for the throttler
import re    # NEW: Needed for smarter score extraction

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")
st.title("🎯 HireSync AI: Recruiter Dashboard")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ System Key Active")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")
    
    if st.button("🔄 Reset All Data"):
        st.session_state.analysis_results = []
        st.rerun()

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except: return ""

def get_gemini_score(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        # 2026 Update: Use gemini-1.5-flash for max stability on free tier
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        Analyze Resume vs JD. 
        Return STRICTLY in this format: Score | Internal Review | Applicant Guidance
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- Input Section ---
job_description = st.text_area("📋 Paste Job Description (JD):", height=150)
uploaded_files = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True)

# --- Processing Section ---
if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Missing Info.")
    else:
        temp_results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            with st.spinner(f"Analyzing {file.name}..."):
                text = extract_text_from_pdf(file)
                if text.strip():
                    analysis = get_gemini_score(text, job_description, api_key)
                    
                    # --- FIXED PARSING ---
                    try:
                        parts = analysis.split("|")
                        # Use Regex to find the first number in the score part
                        score_match = re.search(r'\d+', parts[0])
                        score = int(score_match.group()) if score_match else 0
                        
                        temp_results.append({
                            "Name": file.name,
                            "Score": score,
                            "Recruiter_Notes": parts[1].strip() if len(parts) > 1 else "No data",
                            "Applicant_Notes": parts[2].strip() if len(parts) > 2 else "No data"
                        })
                    except: continue
            
            # --- THE THROTTLER (Crucial Fix) ---
            # If we have more files to go, wait 4 seconds to stay under 15 RPM
            if i < len(uploaded_files) - 1:
                time.sleep(4) 
                
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.session_state.analysis_results = temp_results

# --- Display Section ---
if st.session_state.analysis_results:
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    for index, row in df.iterrows():
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            st.write(f"**Review:** {row['Recruiter_Notes']}")
            st.write(f"**Tips:** {row['Applicant_Notes']}")
            if st.button("Shortlist", key=f"sl_{index}"):
                st.success(f"Saved {row['Name']}!")
