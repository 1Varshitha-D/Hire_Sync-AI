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
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""
        Analyze Resume vs JD. 
        Format strictly: Score | Internal Review | Applicant Guidance
        - Internal Review: Professional critique for HR.
        - Applicant Guidance: Encouraging tips for the candidate.
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
    job_description = st.text_area("📋 Job Description", height=150, placeholder="Paste JD here...")
with col_b:
    uploaded_files = st.file_uploader("📂 Upload Resumes", type="pdf", accept_multiple_files=True)

if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Missing Input Fields")
    else:
        temp_results = []
        progress_bar = st.progress(0)
        for i, file in enumerate(uploaded_files):
            text = extract_text_from_pdf(file)
            if text:
                res = get_gemini_analysis(text, job_description, api_key)
                try:
                    parts = res.split("|")
                    score = int(re.search(r'\d+', parts[0]).group())
                    temp_results.append({
                        "Name": file.name, "Score": score,
                        "Recruiter": parts[1].strip(), "Applicant": parts[2].strip()
                    })
                except: continue
            if i < len(uploaded_files) - 1:
                time.sleep(4) 
            progress_bar.progress((i + 1) / len(uploaded_files))
        st.session_state.analysis_results = temp_results

# --- 6. The User-Friendly Tabs View ---
if st.session_state.analysis_results:
    st.markdown("---")
    
    # Define the three main sections of your app
    tab1, tab2, tab3 = st.tabs(["🏢 Recruiter Dashboard", "🎓 Applicant Feedback", "⭐ Final Shortlist"])

    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)

    # --- TAB 1: RECRUITER VIEW ---
    with tab1:
        st.header("Internal Ranking & Notes")
        for idx, row in df.iterrows():
            with st.expander(f"📊 {row['Score']}% - {row['Name']}"):
                st.markdown("**Hiring Manager's Notes:**")
                st.info(row['Recruiter'])
                if st.button(f"➕ Shortlist {row['Name']}", key=f"rec_{idx}"):
                    if row['Name'] not in st.session_state.shortlisted_candidates:
                        st.session_state.shortlisted_candidates.append(row['Name'])
                        st.toast(f"Added {row['Name']} to shortlist!")

    # --- TAB 2: APPLICANT VIEW ---
    with tab2:
        st.header("Candidate Improvement Guidance")
        st.write("Share these insights with your applicants to help them grow.")
        for idx, row in df.iterrows():
            with st.expander(f"💡 Feedback for {row['Name']}"):
                st.markdown("**Personalized Guidance:**")
                st.success(row['Applicant'])

    # --- TAB 3: SHORTLIST VIEW ---
    with tab3:
        st.header("Selected Candidates")
        if not st.session_state.shortlisted_candidates:
            st.info("No one has been shortlisted yet.")
        else:
            # Display names in a clean list
            for name in st.session_state.shortlisted_candidates:
                st.markdown(f"- **{name}**")
            
            # Exclusive download for shortlisted data
            sl_df = df[df['Name'].isin(st.session_state.shortlisted_candidates)]
            csv = sl_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Final Shortlist", data=csv, file_name="shortlist_2026.csv")
