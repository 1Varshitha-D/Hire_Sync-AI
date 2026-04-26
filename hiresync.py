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

def get_gemini_analysis(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"""
        Analyze Resume vs JD. 
        Format strictly: Score | Internal Review | Applicant Guidance
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
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
                if text.strip():
                    analysis = get_gemini_score(text, job_description, api_key)
                    
                    # Robust Parsing
                    try:
                        if "|" in analysis:
                            parts = analysis.split("|")
                            score_digits = ''.join(filter(str.isdigit, parts[0]))
                            score = int(score_digits) if score_digits else 0
                            
                            temp_results.append({
                                "Name": file.name,
                                "Score": score,
                                "Recruiter_Notes": parts[1].strip() if len(parts) > 1 else "Analysis failed",
                                "Applicant_Notes": parts[2].strip() if len(parts) > 2 else "No guidance provided"
                            })
                    except:
                        continue
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Save to memory!
        st.session_state.analysis_results = temp_results

# --- 6. Results Display ---
if st.session_state.analysis_results:
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🏢 Recruiter Dashboard", "🎓 Applicant Feedback", "⭐ Final Shortlist"])
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)

    with tab1:
        st.header("Internal Ranking")
        for idx, row in df.iterrows():
            with st.expander(f"📊 {row['Score']}% - {row['Name']}"):
                st.info(row['Recruiter'])
                # Use a unique key for the button to avoid conflicts
                if st.button(f"➕ Shortlist {row['Name']}", key=f"short_{idx}"):
                    if row['Name'] not in st.session_state.shortlisted_candidates:
                        st.session_state.shortlisted_candidates.append(row['Name'])
                        st.toast(f"{row['Name']} Shortlisted!")
                        st.balloons()

    with tab2:
        st.header("Applicant Guidance")
        for idx, row in df.iterrows():
            with st.expander(f"💡 Feedback for {row['Name']}"):
                st.success(row['Applicant'])

    with tab3:
        st.header("Selected Shortlist")
        if not st.session_state.shortlisted_candidates:
            st.info("No candidates selected.")
        else:
            for name in st.session_state.shortlisted_candidates:
                st.markdown(f"✅ **{name}**")
            
            # Allow downloading the specific shortlisted data
            short_df = df[df['Name'].isin(st.session_state.shortlisted_candidates)]
            st.download_button("📥 Download Shortlist CSV", data=short_df.to_csv(index=False), file_name="shortlist.csv")
