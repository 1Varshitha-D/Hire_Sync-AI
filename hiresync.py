import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

st.title("🎯 HireSync AI: Recruiter Dashboard")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    # Manual entry - no "Secrets" logic here
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    
    if st.button("Clear Results"):
        st.session_state.analysis_results = []
        st.rerun()

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
        Compare this Resume to the Job Description. 
        Return ONLY this format: Score: [0-100] | Review: [text] | Guidance: [text]
        
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Main App ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

jd_input = st.text_area("📋 Paste Job Description (JD):", height=150)
files_input = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True)

if st.button("🚀 Run Analysis"):
    if not api_key or not jd_input or not files_input:
        st.error("Missing API Key, JD, or Resumes!")
    else:
        results = []
        progress = st.progress(0)
        for i, file in enumerate(files_input):
            text = extract_text_from_pdf(file)
            analysis = get_gemini_analysis(text, jd_input, api_key)
            
            # Simple split logic
            parts = analysis.split("|")
            # Cleaning the score (removes letters, keeps numbers)
            score_raw = parts[0].replace("Score:", "").strip()
            score = ''.join(filter(str.isdigit, score_raw))
            
            results.append({
                "Name": file.name,
                "Score": int(score) if score else 0,
                "Review": parts[1].strip() if len(parts) > 1 else "No review",
                "Guidance": parts[2].strip() if len(parts) > 2 else "No guidance"
            })
            progress.progress((i + 1) / len(files_input))
        st.session_state.analysis_results = results

# --- Display Results ---
if st.session_state.analysis_results:
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    for index, row in df.iterrows():
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            st.warning(f"**Internal Review:** {row['Review']}")
            st.info(f"**Applicant Guidance:** {row['Guidance']}")
