import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")
st.subheader("Dual-View Analysis")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        return f"Error: {e}"

def get_gemini_score(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"""
        Analyze Resume vs JD. Return STRICTLY: Score | Internal Review | Applicant Guidance
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Input Section ---
job_description = st.text_area("📋 Paste Job Description (JD):", height=150)
uploaded_files = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True)

# --- Memory Management (Session State) ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

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
                    parts = analysis.split("|")
                    score = int(''.join(filter(str.isdigit, parts[0]))) if "|" in analysis else 0
                    temp_results.append({
                        "Name": file.name,
                        "Score": score,
                        "Recruiter_Notes": parts[1].strip() if len(parts) > 1 else "Error",
                        "Applicant_Notes": parts[2].strip() if len(parts) > 2 else "N/A"
                    })
                except:
                    pass
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Save to memory!
        st.session_state.analysis_results = temp_results

# --- Display Results from Memory ---
if st.session_state.analysis_results:
    st.markdown("---")
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    for index, row in df.iterrows():
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🏢 Company Internal Review")
                st.warning(row["Recruiter_Notes"])
            with c2:
                st.markdown("#### 🎓 Applicant Guidance")
                st.info(row["Applicant_Notes"])
            
            # These buttons will now work because the data is in st.session_state
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("Shortlist", key=f"sl_{index}"):
                    st.success(f"Shortlisted {row['Name']}!")
            with col_btn2:
                if st.button("Send Feedback", key=f"fb_{index}"):
                    st.info(f"Feedback prepared for {row['Name']}")
