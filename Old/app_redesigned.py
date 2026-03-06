"""
Simple JobFit Analyzer - REDESIGNED
====================================

Single Upload → Multiple Analysis Views

Upload JD and Resume ONCE, see results in different tabs:
- Skills Validation
- Technology Keywords  
- JD Summary & Search Strings
"""

import os
import json
import re
import streamlit as st
import fitz  # PyMuPDF
import docx
from dotenv import load_dotenv

from simple_top5_validator import SimpleTop5Validator
from security_masker import SecurityMasker, create_masking_audit_log

# Load environment
load_dotenv()

# Page config
st.set_page_config(
    page_title="Simple JobFit Analyzer",
    page_icon="🎯",
    layout="wide"
)

# Initialize in session state
if 'validator' not in st.session_state:
    api_key = os.getenv("GROQ_API_KEY")
    st.session_state.validator = SimpleTop5Validator(api_key=api_key)
    st.session_state.masker = SecurityMasker()
    st.session_state.masking_audit_log = []
    
    # Analysis results storage
    st.session_state.jd_uploaded = False
    st.session_state.resume_uploaded = False
    st.session_state.jd_text = None
    st.session_state.resume_text = None
    st.session_state.candidate_name = None
    
    # Analysis results
    st.session_state.comprehensive_skills = None
    st.session_state.tech_keywords = None
    st.session_state.jd_summary = None
    st.session_state.validation_results = None

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

# Title
st.title("🎯 Simple JobFit Analyzer")
st.caption("Upload JD and Resume once - See multiple analysis views | 🔒 PII Protected")

# ========================================
# MAIN UPLOAD SECTION (Always Visible)
# ========================================

st.header("📤 Upload Documents")

# Security settings
with st.expander("🔒 Security Settings", expanded=False):
    col_sec1, col_sec2, col_sec3 = st.columns(3)
    
    with col_sec1:
        enable_pii_masking = st.checkbox(
            "🔒 Mask Resume PII", 
            value=True, 
            help="Masks emails, phones, addresses from resumes"
        )
    
    with col_sec2:
        enable_jd_masking = st.checkbox(
            "🏢 Mask JD Client Info", 
            value=True,
            help="Masks client names, project codes, budget info from JDs"
        )
    
    with col_sec3:
        if st.session_state.masking_audit_log:
            st.metric("Items Masked", len(st.session_state.masking_audit_log))

# Upload section
col_upload1, col_upload2 = st.columns(2)

# JD Upload
with col_upload1:
    st.subheader("📄 Job Description")
    
    jd_file = st.file_uploader(
        "Upload JD (PDF/DOCX/TXT)",
        type=["pdf", "docx", "txt"],
        key="main_jd_file",
        help="Upload once - analyzed in all tabs"
    )
    
    if jd_file:
        if not st.session_state.jd_uploaded or st.session_state.get('last_jd_name') != jd_file.name:
            with st.spinner("📖 Reading JD..."):
                jd_text = extract_text_from_file(jd_file)
                
                if jd_text:
                    # Apply JD masking if enabled
                    if enable_jd_masking:
                        with st.spinner("🔒 Masking client info..."):
                            jd_masking_result = st.session_state.masker.mask_jd(
                                jd_text,
                                known_client_names=[]
                            )
                            jd_text = jd_masking_result.masked_text
                            
                            if jd_masking_result.mask_count > 0:
                                audit_entry = create_masking_audit_log(jd_masking_result, "jd")
                                audit_entry['filename'] = jd_file.name
                                st.session_state.masking_audit_log.append(audit_entry)
                    
                    # Store JD
                    st.session_state.jd_text = jd_text
                    st.session_state.jd_uploaded = True
                    st.session_state.last_jd_name = jd_file.name
                    
                    # Analyze JD (all analyses)
                    with st.spinner("🤖 Analyzing JD..."):
                        # 1. Extract comprehensive skills
                        st.session_state.comprehensive_skills = st.session_state.validator.extract_top_5_skills(jd_text)
                        
                        # 2. Extract tech keywords
                        if st.session_state.validator.use_llm:
                            try:
                                from groq import Groq
                                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                                
                                # Tech keywords
                                tech_prompt = f"""Extract ONLY technology keywords from this JD:
{jd_text[:2000]}

Return JSON array of 10-15 tech keywords:
["keyword1", "keyword2", ...]"""

                                tech_response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": tech_prompt}],
                                    temperature=0.1,
                                    max_tokens=400
                                )
                                
                                tech_result = tech_response.choices[0].message.content.strip()
                                if "```" in tech_result:
                                    tech_result = re.search(r'```(?:json)?\s*(.*?)\s*```', tech_result, re.DOTALL).group(1)
                                
                                st.session_state.tech_keywords = json.loads(tech_result)
                                
                                # 3. Generate JD summary
                                summary_prompt = f"""Analyze this JD and provide:
{jd_text[:3000]}

Return JSON:
{{
  "role_summary": "...",
  "role_combination": "...",
  "key_requirements": ["...", "..."],
  "naukri_searches": ["...", "..."],
  "linkedin_searches": ["...", "..."]
}}"""

                                summary_response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": summary_prompt}],
                                    temperature=0.2,
                                    max_tokens=1500
                                )
                                
                                summary_result = summary_response.choices[0].message.content.strip()
                                if "```" in summary_result:
                                    summary_result = re.search(r'```(?:json)?\s*(.*?)\s*```', summary_result, re.DOTALL).group(1)
                                
                                st.session_state.jd_summary = json.loads(summary_result)
                                
                            except:
                                st.session_state.tech_keywords = []
                                st.session_state.jd_summary = None
                    
                    st.success(f"✅ JD Analyzed: {jd_file.name}")
    
    # Show JD status
    if st.session_state.jd_uploaded:
        st.success("✅ JD Ready")
        st.caption(f"📄 {st.session_state.get('last_jd_name', 'JD uploaded')}")
        if st.session_state.comprehensive_skills:
            st.caption(f"🎯 {len(st.session_state.comprehensive_skills)} skills extracted")

# Resume Upload
with col_upload2:
    st.subheader("📄 Resume")
    
    if st.session_state.jd_uploaded:
        resume_file = st.file_uploader(
            "Upload Resume (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="main_resume_file",
            help="Upload once - validated against all analyses"
        )
        
        if resume_file:
            if not st.session_state.resume_uploaded or st.session_state.get('last_resume_name') != resume_file.name:
                with st.spinner("📖 Reading Resume..."):
                    resume_text = extract_text_from_file(resume_file)
                    
                    if resume_text:
                        # Extract candidate name
                        first_line = resume_text.split('\n')[0].strip()
                        candidate_name = first_line if len(first_line) < 50 else "Candidate"
                        
                        # Apply PII masking
                        if enable_pii_masking:
                            with st.spinner("🔒 Masking PII..."):
                                masking_result = st.session_state.masker.mask_resume(resume_text)
                                resume_text = masking_result.masked_text
                                
                                if masking_result.mask_count > 0:
                                    audit_entry = create_masking_audit_log(masking_result, "resume")
                                    audit_entry['filename'] = resume_file.name
                                    audit_entry['candidate_name'] = candidate_name
                                    st.session_state.masking_audit_log.append(audit_entry)
                        
                        # Store resume
                        st.session_state.resume_text = resume_text
                        st.session_state.candidate_name = candidate_name
                        st.session_state.resume_uploaded = True
                        st.session_state.last_resume_name = resume_file.name
                        
                        # Validate
                        with st.spinner(f"🔍 Validating {candidate_name}..."):
                            fit_score, validations = st.session_state.validator.validate_candidate(
                                st.session_state.comprehensive_skills,
                                resume_text,
                                candidate_name
                            )
                            
                            st.session_state.validation_results = {
                                'fit_score': fit_score,
                                'validations': validations
                            }
                        
                        st.success(f"✅ Resume Validated: {candidate_name}")
        
        # Show resume status
        if st.session_state.resume_uploaded:
            st.success("✅ Resume Ready")
            st.caption(f"👤 {st.session_state.candidate_name}")
            if st.session_state.validation_results:
                st.metric("Fit Score", f"{st.session_state.validation_results['fit_score']:.0f}/100")
    else:
        st.info("👈 Upload JD first")

st.divider()

# ========================================
# TABS (Results Display)
# ========================================

if st.session_state.jd_uploaded:
    main_tabs = st.tabs(["🎯 Skills Validation", "🔧 Technology Keywords", "📋 JD Summary", "ℹ️ How It Works"])
    
    # TAB 1: Skills Validation
    with main_tabs[0]:
        st.header("🎯 Skills Validation Results")
        
        if st.session_state.resume_uploaded and st.session_state.validation_results:
            results = st.session_state.validation_results
            
            # Fit score
            if results['fit_score'] >= 75:
                st.success(f"### ✅ STRONG FIT - {results['fit_score']:.0f}/100")
            elif results['fit_score'] >= 60:
                st.warning(f"### ⚠️ CONDITIONAL FIT - {results['fit_score']:.0f}/100")
            else:
                st.error(f"### ❌ WEAK FIT - {results['fit_score']:.0f}/100")
            
            st.divider()
            
            # Skill-by-skill
            st.subheader("🔍 Skill Assessment")
            
            for i, val in enumerate(results['validations'], 1):
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
            
            # Summary
            st.divider()
            validated_count = sum(1 for v in results['validations'] if v.has_project_experience)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Skills with Projects", f"{validated_count}/{len(results['validations'])}")
            col2.metric("Average Score", f"{results['fit_score']:.0f}%")
            col3.metric("Skills Missing", f"{len(results['validations']) - validated_count}")
            
            # Export
            st.divider()
            report_md = st.session_state.validator.generate_simple_report(
                st.session_state.candidate_name,
                st.session_state.comprehensive_skills,
                results['fit_score'],
                results['validations']
            )
            
            st.download_button(
                "📥 Download Report",
                data=report_md,
                file_name=f"validation_{st.session_state.candidate_name.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.info("👆 Upload resume to see validation results")
    
    # TAB 2: Technology Keywords
    with main_tabs[1]:
        st.header("🔧 Technology Keywords")
        
        if st.session_state.tech_keywords:
            st.success(f"✅ Extracted {len(st.session_state.tech_keywords)} technology keywords")
            
            # Categorize
            categories = {
                "AI/ML": ["genai", "rag", "llm", "ml", "ai"],
                "Cloud": ["aws", "azure", "gcp", "cloud"],
                "Languages": ["python", "java", "javascript"],
                "Databases": ["sql", "mongodb", "postgresql"],
                "DevOps": ["docker", "kubernetes", "jenkins"],
                "Other": []
            }
            
            categorized = {cat: [] for cat in categories.keys()}
            
            for kw in st.session_state.tech_keywords:
                kw_lower = kw.lower()
                found = False
                for cat, markers in categories.items():
                    if cat != "Other" and any(m in kw_lower for m in markers):
                        categorized[cat].append(kw)
                        found = True
                        break
                if not found:
                    categorized["Other"].append(kw)
            
            for cat, kws in categorized.items():
                if kws:
                    with st.expander(f"📂 {cat} ({len(kws)})", expanded=True):
                        cols = st.columns(3)
                        for idx, kw in enumerate(kws):
                            cols[idx % 3].write(f"• {kw}")
        else:
            st.info("No tech keywords extracted")
    
    # TAB 3: JD Summary
    with main_tabs[2]:
        st.header("📋 JD Summary & Search Strings")
        
        if st.session_state.jd_summary:
            summary = st.session_state.jd_summary
            
            st.subheader("📋 Role Summary")
            st.info(summary.get("role_summary", ""))
            
            st.subheader("🔄 Role Combination")
            st.success(f"### {summary.get('role_combination', 'N/A')}")
            
            st.divider()
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.subheader("🟢 Naukri Searches")
                for i, s in enumerate(summary.get("naukri_searches", []), 1):
                    st.code(s, language=None)
            
            with col_s2:
                st.subheader("🔵 LinkedIn Searches")
                for i, s in enumerate(summary.get("linkedin_searches", []), 1):
                    st.code(s, language=None)
        else:
            st.info("No summary available")
    
    # TAB 4: How It Works
    with main_tabs[3]:
        st.header("ℹ️ How This Tool Works")
        st.markdown("""
        ### Upload Once, Multiple Views
        
        1. Upload JD → System analyzes it 3 ways:
           - Comprehensive skills
           - Technology keywords
           - JD summary
        
        2. Upload Resume → System validates against all
        
        3. Switch tabs to see different views
        
        ### Benefits
        - ✅ No repeated uploads
        - ✅ Consistent data across tabs
        - ✅ Fast switching between views
        """)

else:
    st.info("📤 Upload a Job Description to get started")

# Footer with security
if st.session_state.masking_audit_log:
    with st.expander("🔒 Security Audit Log"):
        import pandas as pd
        df = pd.DataFrame(st.session_state.masking_audit_log)
        st.dataframe(df, use_container_width=True)
