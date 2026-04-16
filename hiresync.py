import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import re

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")
st.subheader("Analyze Resumes against Job Descriptions instantly.")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    # This allows you to paste the key directly in the app
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
    except Exception as e:
        return ""

def get_gemini_analysis(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        # Using the most stable model name to avoid 404 errors
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
        You are an expert recruiter. Compare the Resume to the Job Description (JD).
        Provide the output in this EXACT format:
        Score: [0-100] | Review: [Detailed internal notes] | Guidance: [Tips for the candidate]
        
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Main Input Section ---
jd_input = st.text_area("📋 Paste Job Description (JD):", height=150)
files_input = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True)

if st.button("🚀 Run Analysis"):
    if not api_key or not jd_input or not files_input:
        st.error("Please provide your API Key, the JD, and at least one Resume.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(files_input):
            with st.spinner(f"Analyzing {file.name}..."):
                text = extract_text_from_pdf(file)
                if not text:
                    results.append({"Name": file.name, "Score": 0, "Review": "Could not read PDF text.", "Guidance": "N/A"})
                    continue
                
                analysis = get_gemini_analysis(text, jd_input, api_key)
                
                # --- Smart Parsing Logic ---
                try:
                    # Find the score using Regex (finds the first number in the response)
                    score_match = re.search(r'\d+', analysis)
                    score = int(score_match.group()) if score_match else 0
                    
                    # Split the response by the pipe symbol
                    parts = analysis.split("|")
                    review = parts[1].replace("Review:", "").strip() if len(parts) > 1 else "Analysis successful."
                    guidance = parts[2].replace("Guidance:", "").strip() if len(parts) > 2 else "Check resume for improvements."
                    
                    results.append({
                        "Name": file.name,
                        "Score": score,
                        "Review": review,
                        "Guidance": guidance
                    })
                except:
                    results.append({"Name": file.name, "Score": 0, "Review": "Error parsing AI response.", "Guidance": "N/A"})
            
            progress_bar.progress((i + 1) / len(files_input))
        
        st.session_state.analysis_results = results

# --- Display Results ---
if st.session_state.analysis_results:
    st.markdown("---")
    # Sort results by score (highest first)
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    for index, row in df.iterrows():
        # Score color coding
        score_color = "🟢" if row['Score'] >= 70 else "🟡" if row['Score'] >= 40 else "🔴"
        
        with st.expander(f"{score_color} {row['Score']}% — {row['Name']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏢 Internal Review")
                st.warning(row['Review'])
            with col2:
                st.subheader("🎓 Candidate Guidance")
                st.info(row['Guidance'])

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
