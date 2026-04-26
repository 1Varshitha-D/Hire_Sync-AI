import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import time
import re

# --- 1. Page Configuration ---
st.set_page_config(page_title="HireSync AI", page_icon="🎯", layout="wide")

# --- 2. Custom Styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stProgress > div > div > div > div { background-color: #007bff; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Sidebar & API Management ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=100)
    st.header("Control Panel")
    
    # Priority: Secrets (Deployment) > Manual Input
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ System API Key Active")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password", help="Get a free key from Google AI Studio")
        st.info("No card required for free tier.")

    st.markdown("---")
    if st.button("🔄 Clear All Analysis"):
        st.session_state.analysis_results = []
        st.rerun()

# --- 4. Helper Functions ---
def extract_text_from_pdf(file):
    """Extracts text from uploaded PDF files safely."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def get_gemini_analysis(resume_text, jd, api_key):
    """Calls Gemini 2.5 Flash to analyze the resume against the JD."""
    try:
        genai.configure(api_key=api_key)
        # Using Gemini 2.5 Flash - The 2026 stable workhorse for free tier
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        You are an expert HR Recruiter. Compare the Resume provided against the Job Description (JD).
        Return your response strictly in this pipe-separated format:
        Score | Internal Review | Applicant Guidance
        
        - Score: A number from 0-100.
        - Internal Review: 2-3 sentences for the hiring manager.
        - Applicant Guidance: 2-3 specific tips for the candidate to improve.

        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- 5. Session State Initialization ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- 6. Main UI ---
st.title("🎯 HireSync AI")
st.subheader("Automated Multi-Resume Screening & Feedback")

col_a, col_b = st.columns([1, 1])

with col_a:
    job_description = st.text_area("📋 Job Description", height=200, placeholder="Paste the job requirements here...")

with col_b:
    uploaded_files = st.file_uploader("📂 Upload Resumes (PDF)", type="pdf", accept_multiple_files=True)

# --- 7. Processing Logic ---
if st.button("🚀 Start Dual-View Analysis"):
    if not api_key:
        st.error("Please provide an API Key in the sidebar.")
    elif not job_description or not uploaded_files:
        st.warning("Please provide both a Job Description and at least one Resume.")
    else:
        temp_results = []
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            progress_text.text(f"Analyzing {file.name} ({i+1}/{len(uploaded_files)})...")
            
            # Extract and Call AI
            resume_content = extract_text_from_pdf(file)
            if resume_content:
                raw_analysis = get_gemini_analysis(resume_content, job_description, api_key)
                
                # Robust Parsing with Regex for the score
                try:
                    parts = raw_analysis.split("|")
                    score_match = re.search(r'\d+', parts[0])
                    score_val = int(score_match.group()) if score_match else 0
                    
                    temp_results.append({
                        "Name": file.name,
                        "Score": score_val,
                        "Recruiter": parts[1].strip() if len(parts) > 1 else "Analysis Error",
                        "Applicant": parts[2].strip() if len(parts) > 2 else "Check back later"
                    })
                except:
                    continue

            # --- THE CRITICAL FIX: The Throttler ---
            # To stay under the 15 Requests Per Minute free limit, 
            # we wait 4 seconds between files if there are more to process.
            if i < len(uploaded_files) - 1:
                time.sleep(4) 
            
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        st.session_state.analysis_results = temp_results
        progress_text.text("✅ Analysis Complete!")

# --- 8. Display Results ---
if st.session_state.analysis_results:
    st.markdown("---")
    # Sort by highest score automatically
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    st.header("🏆 Candidate Rankings")
    
    for idx, row in df.iterrows():
        # Color coding the expander header based on score
        color = "🟢" if row['Score'] > 75 else "🟡" if row['Score'] > 40 else "🔴"
        
        with st.expander(f"{color} {row['Score']}% — {row['Name']}"):
            rec, app = st.columns(2)
            with rec:
                st.markdown("##### 🏢 For the Recruiter")
                st.info(row['Recruiter'])
            with app:
                st.markdown("##### 🎓 For the Applicant")
                st.success(row['Applicant'])
            
            if st.button(f"Shortlist {row['Name']}", key=f"btn_{idx}"):
                st.balloons()
                st.toast(f"{row['Name']} added to shortlist!")

    # Global Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download All Results (CSV)", data=csv, file_name="hiresync_analysis.csv", mime="text/csv")
