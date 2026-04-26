import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import time
import re

# --- 1. Page Configuration ---
st.set_page_config(page_title="HireSync AI", page_icon="🎯", layout="wide")

# --- 2. Sidebar & API Management ---
with st.sidebar:
    st.header("⚙️ Settings")
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ System Key Active")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")

    st.markdown("---")
    if st.button("🔄 Reset All Data"):
        st.session_state.analysis_results = []
        st.session_state.shortlisted_candidates = []
        st.rerun()

# --- 3. Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def get_gemini_analysis(resume_text, jd, api_key, retries=2):
    try:
        genai.configure(api_key=api_key)
        # FIXED: Using the 2026 stable string
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"Analyze Resume vs JD. Format: Score | Review | Guidance\nJD: {jd}\nResume: {resume_text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        if "429" in str(e) and retries > 0:
            st.warning("⚠️ Quota hit. Waiting 30s...")
            time.sleep(30)
            return get_gemini_analysis(resume_text, jd, api_key, retries - 1)
        return f"0 | Error: {str(e)} | N/A"

# --- 4. Initialize Session States ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []
if "shortlisted_candidates" not in st.session_state:
    st.session_state.shortlisted_candidates = []

# --- 5. Main UI ---
st.title("🎯 HireSync AI")
col_a, col_b = st.columns([1, 1])

with col_a:
    job_description = st.text_area("📋 Job Description", height=150)
with col_b:
    uploaded_files = st.file_uploader("📂 Upload Resumes", type="pdf", accept_multiple_files=True)

if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Missing Input")
    else:
        st.session_state.analysis_results = []
        status_text = st.empty() 
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            status_text.markdown(f"🔍 **Processing:** {file.name}")
            text = extract_text_from_pdf(file)
            if text.strip():
                analysis = get_gemini_analysis(text, job_description, api_key)
                try:
                    parts = analysis.split("|")
                    score = int(re.search(r'\d+', parts[0]).group())
                    st.session_state.analysis_results.append({
                        "Name": file.name, "Score": score,
                        "Recruiter": parts[1].strip(), "Applicant": parts[2].strip()
                    })
                except: continue
            
            if i < len(uploaded_files) - 1:
                time.sleep(5) # Throttler
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.success("✅ Analysis Complete!")

# --- 6. The Tabs View ---
if st.session_state.analysis_results:
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🏢 Recruiter Dashboard", "🎓 Applicant Feedback", "⭐ Final Shortlist"])
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)

    with tab1:
        for idx, row in df.iterrows():
            with st.expander(f"📊 {row['Score']}% - {row['Name']}"):
                st.info(row['Recruiter'])
                if st.button(f"➕ Shortlist {row['Name']}", key=f"r_{idx}"):
                    if row['Name'] not in st.session_state.shortlisted_candidates:
                        st.session_state.shortlisted_candidates.append(row['Name'])
                        st.toast("Added!")

    with tab2:
        for idx, row in df.iterrows():
            with st.expander(f"💡 Guidance for {row['Name']}"):
                st.success(row['Applicant'])

    with tab3:
        if st.session_state.shortlisted_candidates:
            for name in st.session_state.shortlisted_candidates:
                st.markdown(f"- **{name}**")
            sl_df = df[df['Name'].isin(st.session_state.shortlisted_candidates)]
            st.download_button("📥 Download Shortlist", data=sl_df.to_csv(index=False), file_name="shortlist.csv")
