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
    """Self-healing function to handle 404 and 429 errors."""
    try:
        genai.configure(api_key=api_key)
        
        # --- THE FIX: Try the 3 most common 2026 model strings ---
        # If 'gemini-1.5-flash' fails, the 'except' block will try the others.
        model_name = "gemini-1.5-flash" 
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Analyze Resume vs JD. 
        Format strictly: Score | Internal Review | Applicant Guidance
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        error_msg = str(e)
        
        # Handle Quota Limit (429)
        if "429" in error_msg and retries > 0:
            st.warning("⚠️ Speed limit hit. Waiting 30s...")
            time.sleep(30)
            return get_gemini_analysis(resume_text, jd, api_key, retries - 1)
        
        # Handle Model Not Found (404) - Try a different model name automatically
        if "404" in error_msg and "gemini-1.5-flash" in model_name:
            # Try the 'latest' alias if the standard name fails
            try:
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                response = model.generate_content(prompt)
                return response.text.strip()
            except:
                pass
                
        return f"0 | Error: {error_msg} | N/A"

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
    uploaded_files = st.file_uploader("📂 Upload Resumes (PDF)", type="pdf", accept_multiple_files=True)

if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Please provide API Key, JD, and Resumes.")
    else:
        st.session_state.analysis_results = []
        status_text = st.empty() 
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            status_text.markdown(f"🔍 **Analyzing:** {file.name} ({i+1}/{len(uploaded_files)})")
            text = extract_text_from_pdf(file)
            
            if text.strip():
                analysis = get_gemini_analysis(text, job_description, api_key)
                
                try:
                    parts = analysis.split("|")
                    score_match = re.search(r'\d+', parts[0])
                    score = int(score_match.group()) if score_match else 0
                    
                    st.session_state.analysis_results.append({
                        "Name": file.name, "Score": score,
                        "Recruiter": parts[1].strip() if len(parts) > 1 else "Error",
                        "Applicant": parts[2].strip() if len(parts) > 2 else "Error"
                    })
                except: continue
            
            # 5-second wait to stay under the 15 RPM Free Tier limit
            if i < len(uploaded_files) - 1:
                time.sleep(5) 
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.success(f"✅ Finished! Analyzed {len(st.session_state.analysis_results)} resumes.")

# --- 6. Results View ---
if st.session_state.analysis_results:
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🏢 Recruiter Dashboard", "🎓 Applicant Feedback", "⭐ Final Shortlist"])
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)

    with tab1:
        st.header("Recruiter Insights")
        for idx, row in df.iterrows():
            with st.expander(f"📊 {row['Score']}% - {row['Name']}"):
                st.info(row['Recruiter'])
                if st.button(f"➕ Shortlist {row['Name']}", key=f"r_{idx}"):
                    if row['Name'] not in st.session_state.shortlisted_candidates:
                        st.session_state.shortlisted_candidates.append(row['Name'])
                        st.toast(f"Added {row['Name']}!")

    with tab2:
        st.header("Candidate Guidance")
        for idx, row in df.iterrows():
            with st.expander(f"💡 Feedback for {row['Name']}"):
                st.success(row['Applicant'])

    with tab3:
        st.header("Selected Shortlist")
        if not st.session_state.shortlisted_candidates:
            st.info("No candidates shortlisted yet.")
        else:
            for name in st.session_state.shortlisted_candidates:
                st.markdown(f"✅ **{name}**")
            
            sl_df = df[df['Name'].isin(st.session_state.shortlisted_candidates)]
            st.download_button("📥 Download Shortlist", data=sl_df.to_csv(index=False), file_name="shortlist_2026.csv")
