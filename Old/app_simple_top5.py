"""
Simple JobFit Analyzer - Top 5 Skills Only
===========================================

Clean, simple interface:
1. Upload JD → Get top 5 skills
2. Upload Resume → Validate project experience
3. See clear results

No complexity, just what you need.
"""

import os
import streamlit as st
import fitz  # PyMuPDF
import docx
from dotenv import load_dotenv

from simple_top5_validator import SimpleTop5Validator

# Load environment
load_dotenv()

# Page config
st.set_page_config(
    page_title="Simple JobFit Analyzer",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 Simple JobFit Analyzer")
st.caption("Extract top 5 skills from JD and validate against resume")

# Initialize validator
if 'validator' not in st.session_state:
    api_key = os.getenv("GROQ_API_KEY")
    st.session_state.validator = SimpleTop5Validator(api_key=api_key)
    st.session_state.top_5_skills = None

# Helper functions
def extract_text_from_pdf(pdf_file):
    """Extract text from PDF"""
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(docx_file):
    """Extract text from DOCX"""
    try:
        doc = docx.Document(docx_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text_from_file(file):
    """Extract text from uploaded file"""
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    elif file.type == "text/plain":
        return file.read().decode("utf-8")
    else:
        st.error(f"Unsupported file type: {file.type}")
        return ""

# Sidebar - API Status
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if st.session_state.validator.use_llm:
        st.success("🤖 LLM Mode: ACTIVE")
        st.caption("Using Groq API for intelligent extraction")
    else:
        st.warning("📝 Regex Mode: ACTIVE")
        st.caption("LLM unavailable - using keyword matching")
        st.info("💡 Set GROQ_API_KEY for better accuracy")
    
    st.divider()
    st.markdown("""
    ### How It Works
    1. Upload JD → Extracts top 5 skills
    2. Upload Resume → Validates each skill
    3. Get simple Yes/No + score
    
    ### What You Get
    - **Top 5 critical skills** from JD
    - **Project experience validation** for each
    - **Fit score** (0-100)
    - **Simple recommendation**
    """)

# Main content
col1, col2 = st.columns(2)

# Left column - JD Upload
with col1:
    st.header("Step 1: Upload Job Description")
    
    jd_file = st.file_uploader(
        "Upload JD (PDF/DOCX/TXT)",
        type=["pdf", "docx", "txt"],
        key="jd_file"
    )
    
    if jd_file:
        jd_text = extract_text_from_file(jd_file)
        
        if jd_text:
            with st.spinner("🔍 Extracting top 5 skills..."):
                top_5_skills = st.session_state.validator.extract_top_5_skills(jd_text)
                st.session_state.top_5_skills = top_5_skills
            
            st.success("✅ Top 5 Skills Extracted")
            
            st.subheader("🎯 Top 5 Critical Skills")
            for i, skill in enumerate(top_5_skills, 1):
                st.write(f"**{i}.** {skill}")

# Right column - Resume Upload
with col2:
    st.header("Step 2: Upload Resume")
    
    if st.session_state.top_5_skills:
        resume_file = st.file_uploader(
            "Upload Resume (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="resume_file"
        )
        
        if resume_file:
            resume_text = extract_text_from_file(resume_file)
            
            if resume_text:
                # Extract candidate name
                first_line = resume_text.split('\n')[0].strip()
                candidate_name = first_line if len(first_line) < 50 else "Candidate"
                
                with st.spinner(f"🔍 Validating {candidate_name}..."):
                    fit_score, validations = st.session_state.validator.validate_candidate(
                        st.session_state.top_5_skills,
                        resume_text,
                        candidate_name
                    )
                
                st.success("✅ Validation Complete")
                
                # Display fit score
                st.metric(
                    "Fit Score",
                    f"{fit_score:.0f}/100",
                    delta="Strong" if fit_score >= 75 else "Moderate" if fit_score >= 60 else "Weak"
                )
    else:
        st.info("👈 Upload JD first to extract top 5 skills")

# Results section
if st.session_state.top_5_skills and 'resume_file' in st.session_state and st.session_state.resume_file:
    st.divider()
    st.header(f"📊 Validation Results: {candidate_name}")
    
    # Recommendation
    if fit_score >= 75:
        st.success("### ✅ STRONG FIT - Proceed to Interview")
    elif fit_score >= 60:
        st.warning("### ⚠️ CONDITIONAL FIT - Interview with Questions")
    else:
        st.error("### ❌ WEAK FIT - Not Recommended")
    
    st.divider()
    
    # Skill-by-skill breakdown
    st.subheader("🎯 Skill-by-Skill Assessment")
    
    for i, val in enumerate(validations, 1):
        icon = "✅" if val.has_project_experience else "❌"
        
        with st.expander(f"{i}. {icon} {val.skill_name} - {val.validation_score:.0f}%", expanded=True):
            col_a, col_b = st.columns([1, 2])
            
            with col_a:
                if val.has_project_experience:
                    st.success("**Has Project Experience**: Yes")
                else:
                    st.error("**Has Project Experience**: No")
                
                st.metric("Score", f"{val.validation_score:.0f}%")
            
            with col_b:
                st.write(f"**Evidence**: {val.evidence_summary}")
                st.write(f"**Example**: {val.project_example}")
    
    # Summary stats
    st.divider()
    st.subheader("📈 Summary")
    
    validated_count = sum(1 for v in validations if v.has_project_experience)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Skills with Projects", f"{validated_count}/5")
    col2.metric("Average Score", f"{fit_score:.0f}%")
    col3.metric("Skills Missing Projects", f"{5 - validated_count}/5")
    
    # Export report
    st.divider()
    st.subheader("📥 Export Report")
    
    report_md = st.session_state.validator.generate_simple_report(
        candidate_name,
        st.session_state.top_5_skills,
        fit_score,
        validations
    )
    
    st.download_button(
        label="📄 Download Report (Markdown)",
        data=report_md,
        file_name=f"validation_{candidate_name.replace(' ', '_')}.md",
        mime="text/markdown",
        use_container_width=True
    )
    
    # Show report preview
    with st.expander("👁️ Preview Report"):
        st.markdown(report_md)

# Footer
st.divider()
st.caption("🎯 Simple JobFit Analyzer | Top 5 Skills Validation")
