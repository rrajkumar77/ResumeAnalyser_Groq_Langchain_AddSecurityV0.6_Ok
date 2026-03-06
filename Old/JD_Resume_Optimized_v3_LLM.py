"""
TEKsystems JobFit Analyzer - OPTIMIZED v3.0 with Deep Semantic Validation
==========================================================================

**FULL REPLACEMENT VERSION WITH ENHANCED SEMANTIC VALIDATION**

Key Enhancements:
1. ✅ Deep semantic validation - Real project experience vs. claimed knowledge
2. ✅ Experience timeline analysis - Detects resume padding
3. ✅ JD summarization - Extracts mandatory/desired/excluded skills
4. ✅ Evidence-based scoring - Each skill validated with project evidence
5. ✅ Maintained security - PII/client masking fully preserved
6. ✅ Works for single & batch - Consistent validation across both modes

New Features Over v2.0:
- Distinguishes real project work from skill lists
- Timeline validation (claimed vs validated years)
- Auto-generated interview questions for weak skills
- Critical gap identification with improvement suggestions
- Enhanced batch comparison with validation ratios

Original Features Maintained:
- Security masking (PII + client data)
- Interview question generation
- Skills gap analysis
- Batch processing
- Export capabilities
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

import docx
import fitz
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Security masking (PRESERVED)
from security_masker import SecurityMasker, MaskingResult, create_masking_audit_log

# REPLACEMENT: LLM-powered validator for intelligent parsing
try:
    from llm_powered_validator import (
        LLMPoweredResumeValidator as EnhancedResumeValidator
    )
    from semantic_validator_optimized import (
        CandidateValidationReport,
        JDSummary,
        SkillValidation,
        ExperienceType,
        ExperienceTimeline,
        SkillPriority,
        generate_jd_summary_markdown
    )
    LLM_AVAILABLE = True
except Exception as e:
    # Fallback to regex-based if LLM fails
    from semantic_validator_optimized import (
        EnhancedResumeValidator,
        CandidateValidationReport,
        JDSummary,
        SkillValidation,
        ExperienceType,
        ExperienceTimeline,
        SkillPriority,
        generate_jd_summary_markdown
    )
    LLM_AVAILABLE = False
    print(f"⚠️ LLM validator unavailable, using regex-based: {e}")

# Question generators (PRESERVED)
from improved_question_generator import ImprovedQuestionGenerator
from situational_technical_generator import SituationalTechnicalGenerator
from coding_question_generator import CodingQuestionGenerator

# Skill filtering (PRESERVED)
from skill_filter import SkillFilter

# ==================== ENV & MODEL ====================
load_dotenv()

def get_api_key():
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY")

GROQ_API_KEY = get_api_key()
if not GROQ_API_KEY:
    st.warning("⚠️ GROQ_API_KEY not found. Using local validation only.")

# ==================== HELPER FUNCTIONS ====================

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from PDF file."""
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error extracting PDF: {e}")
        return ""

def extract_text_from_docx(docx_file) -> str:
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(docx_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        st.error(f"Error extracting DOCX: {e}")
        return ""

def extract_text_from_file(file) -> str:
    """Extract text from uploaded file (PDF, DOCX, or TXT)."""
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    elif file.type == "text/plain":
        return file.read().decode("utf-8")
    else:
        st.error(f"Unsupported file type: {file.type}")
        return ""

def extract_candidate_name(resume_text: str) -> str:
    """Extract candidate name from resume text."""
    lines = resume_text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line and len(line.split()) <= 4 and len(line) > 3:
            if not any(keyword in line.lower() for keyword in ['email', 'phone', 'address', 'linkedin', 'github']):
                return line
    return "Candidate"

# ==================== SESSION STATE INITIALIZATION ====================

if 'validator' not in st.session_state:
    st.session_state.validator = EnhancedResumeValidator()

if 'jd_summary' not in st.session_state:
    st.session_state.jd_summary = None

if 'jd_text' not in st.session_state:
    st.session_state.jd_text = None

if 'validation_reports' not in st.session_state:
    st.session_state.validation_reports = []

if 'batch_reports' not in st.session_state:
    st.session_state.batch_reports = []

if 'masking_audit_log' not in st.session_state:
    st.session_state.masking_audit_log = []

# ==================== STREAMLIT UI COMPONENTS ====================

def render_jd_summary(jd_summary: JDSummary):
    """Render JD summary in Streamlit."""
    st.subheader("📋 Job Description Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Role Title", jd_summary.role_title)
    with col2:
        st.metric("Role Type", jd_summary.role_archetype)
    
    if jd_summary.core_problem:
        with st.expander("🎯 Core Problem", expanded=True):
            st.info(jd_summary.core_problem)
    
    # Skills breakdown
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🔴 Mandatory ({len(jd_summary.mandatory_skills)})",
        f"🟡 Highly Desired ({len(jd_summary.highly_desired_skills)})",
        f"🟢 Good-to-Have ({len(jd_summary.good_to_have_skills)})",
        f"⛔ Excluded ({len(jd_summary.excluded_skills)})"
    ])
    
    with tab1:
        if jd_summary.mandatory_skills:
            for i, skill in enumerate(jd_summary.mandatory_skills, 1):
                st.write(f"{i}. **{skill.name}**")
        else:
            st.info("No mandatory skills explicitly defined")
    
    with tab2:
        if jd_summary.highly_desired_skills:
            for skill in jd_summary.highly_desired_skills:
                st.write(f"• {skill.name}")
        else:
            st.info("No highly desired skills found")
    
    with tab3:
        if jd_summary.good_to_have_skills:
            for skill in jd_summary.good_to_have_skills:
                st.write(f"• {skill.name}")
        else:
            st.info("No good-to-have skills found")
    
    with tab4:
        if jd_summary.excluded_skills:
            for skill in jd_summary.excluded_skills:
                st.error(f"⛔ {skill.name}")
        else:
            st.info("No excluded skills found")
    
    # Search keywords
    if jd_summary.search_keywords:
        st.divider()
        st.subheader("🔍 Recommended Search Keywords")
        col1, col2 = st.columns(2)
        with col1:
            st.success("**Target Keywords**")
            st.write(", ".join(jd_summary.search_keywords[:15]))
        with col2:
            if jd_summary.reject_keywords:
                st.error("**Reject Keywords**")
                st.write(", ".join(jd_summary.reject_keywords[:10]))

def render_validation_report(report: CandidateValidationReport):
    """Render detailed validation report."""
    st.header(f"📊 Validation Report: {report.candidate_name}")
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if report.overall_fit_score >= 75:
            st.metric("Fit Score", f"{report.overall_fit_score:.0f}/100", delta="Strong", delta_color="normal")
        elif report.overall_fit_score >= 60:
            st.metric("Fit Score", f"{report.overall_fit_score:.0f}/100", delta="Moderate", delta_color="off")
        else:
            st.metric("Fit Score", f"{report.overall_fit_score:.0f}/100", delta="Weak", delta_color="inverse")
    
    with col2:
        st.metric("Real Project Skills", report.real_project_count)
    
    with col3:
        st.metric("Claimed Only", report.claimed_only_count)
    
    with col4:
        st.metric("Critical Gaps", len(report.missing_mandatory_skills))
    
    # Hiring recommendation
    st.divider()
    if "STRONG FIT" in report.hiring_recommendation:
        st.success(f"### {report.hiring_recommendation}")
    elif "CONDITIONAL" in report.hiring_recommendation or "WEAK" in report.hiring_recommendation:
        st.warning(f"### {report.hiring_recommendation}")
    else:
        st.error(f"### {report.hiring_recommendation}")
    
    # Experience timeline
    if report.experience_timeline:
        st.divider()
        st.subheader("⏱️ Experience Timeline Analysis")
        
        timeline = report.experience_timeline
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Claimed", f"{timeline.total_years_claimed:.1f} yrs")
        with col2:
            st.metric("Validated Delivery", f"{timeline.total_years_validated:.1f} yrs")
        with col3:
            if timeline.total_years_claimed > 0:
                ratio = timeline.total_years_validated / timeline.total_years_claimed
                if ratio >= 0.7:
                    st.metric("Validation Ratio", f"{ratio:.0%}", delta="Authentic", delta_color="normal")
                elif ratio >= 0.4:
                    st.metric("Validation Ratio", f"{ratio:.0%}", delta="Moderate", delta_color="off")
                else:
                    st.metric("Validation Ratio", f"{ratio:.0%}", delta="Red Flag", delta_color="inverse")
        
        if timeline.experience_breakdown:
            with st.expander("📊 Experience Breakdown", expanded=False):
                df = pd.DataFrame([
                    {"Category": k, "Years": f"{v:.1f}"}
                    for k, v in timeline.experience_breakdown.items()
                ])
                st.dataframe(df, hide_index=True, use_container_width=True)
        
        if timeline.red_flags:
            st.error("**⚠️ Timeline Red Flags:**")
            for flag in timeline.red_flags:
                st.write(f"• {flag}")
    
    # Validated skills
    st.divider()
    st.subheader("✅ Validated Skills")
    
    if report.validated_skills:
        for skill_val in report.validated_skills:
            icon = "✅" if skill_val.experience_type == ExperienceType.REAL_PROJECT else "⚠️"
            with st.expander(
                f"{icon} {skill_val.skill_name} ({skill_val.validation_score:.0%})",
                expanded=False
            ):
                st.write(f"**Experience Type:** {skill_val.experience_type.value}")
                st.write(f"**Analysis:** {skill_val.gap_analysis}")
                
                if skill_val.evidence:
                    st.write(f"**Project Evidence** ({len(skill_val.evidence)} found):")
                    for i, evidence in enumerate(skill_val.evidence[:2], 1):
                        st.write(f"{i}. Strength: {evidence.evidence_strength:.0%}")
                        if evidence.outcomes:
                            st.write(f"   Outcomes: {', '.join(evidence.outcomes[:2])}")
    else:
        st.info("No validated skills found")
    
    # Weak skills
    if report.weak_skills:
        st.divider()
        st.subheader("⚠️ Weak/Unvalidated Skills")
        
        for skill_val in report.weak_skills[:5]:
            with st.expander(f"⚠️ {skill_val.skill_name}"):
                st.warning(skill_val.gap_analysis)
                
                if skill_val.improvement_suggestions:
                    st.write("**Interview Questions:**")
                    for suggestion in skill_val.improvement_suggestions:
                        st.write(f"• {suggestion}")
    
    # Missing mandatory
    if report.missing_mandatory_skills:
        st.divider()
        st.subheader("❌ Critical Gaps")
        
        for skill in report.missing_mandatory_skills[:10]:
            st.error(f"❌ {skill.name}")
    
    # Interview focus
    if report.interview_focus_areas:
        st.divider()
        st.subheader("🎯 Interview Focus Areas")
        
        for i, area in enumerate(report.interview_focus_areas, 1):
            st.write(f"{i}. {area}")
    
    # Export report
    st.divider()
    st.subheader("📥 Export Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📄 Download Full Report (MD)",
            data=report.detailed_markdown,
            file_name=f"validation_{report.candidate_name}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    with col2:
        summary_df = pd.DataFrame([{
            "Candidate": report.candidate_name,
            "Fit Score": f"{report.overall_fit_score:.0f}%",
            "Real Projects": report.real_project_count,
            "Claimed Only": report.claimed_only_count,
            "Critical Gaps": len(report.missing_mandatory_skills),
            "Recommendation": report.hiring_recommendation.split('-')[0].strip()
        }])
        
        st.download_button(
            label="📊 Download Summary (CSV)",
            data=summary_df.to_csv(index=False),
            file_name=f"summary_{report.candidate_name}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

def render_batch_comparison(reports: List[CandidateValidationReport]):
    """Render comparison table for batch results."""
    st.subheader("📊 Candidate Comparison")
    
    comparison_data = []
    for report in reports:
        timeline = report.experience_timeline
        validation_ratio = 0
        if timeline and timeline.total_years_claimed > 0:
            validation_ratio = timeline.total_years_validated / timeline.total_years_claimed
        
        comparison_data.append({
            "Candidate": report.candidate_name,
            "Fit Score": report.overall_fit_score,
            "Real Projects": report.real_project_count,
            "Claimed Only": report.claimed_only_count,
            "Critical Gaps": len(report.missing_mandatory_skills),
            "Exp. Validation": f"{validation_ratio:.0%}",
            "Recommendation": report.hiring_recommendation.split('-')[0].strip()
        })
    
    df = pd.DataFrame(comparison_data)
    df = df.sort_values('Fit Score', ascending=False)
    
    # Display with formatting
    def color_score(val):
        if isinstance(val, (int, float)):
            if val >= 75:
                return 'background-color: #90EE90'
            elif val >= 60:
                return 'background-color: #FFD700'
            elif val >= 40:
                return 'background-color: #FFA500'
            else:
                return 'background-color: #FF6347'
        return ''
    
    st.dataframe(
        df.style.applymap(color_score, subset=['Fit Score']),
        hide_index=True,
        use_container_width=True
    )
    
    # Export
    st.download_button(
        label="📥 Download Comparison (CSV)",
        data=df.to_csv(index=False),
        file_name=f"batch_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ==================== MAIN APP ====================

st.set_page_config(
    page_title="JobFit Analyzer v3.0",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 JobFit Analyzer v3.0 - Deep Semantic Validation")
st.caption("Enhanced with real project validation, timeline analysis, and experience authenticity detection")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # LLM Status
    if LLM_AVAILABLE and GROQ_API_KEY:
        st.success("🤖 LLM-Powered Validation: ACTIVE")
        st.caption("Using Groq API for intelligent parsing")
    else:
        st.warning("⚠️ LLM-Powered: DISABLED")
        st.caption("Using regex-based parsing (less accurate)")
        if not GROQ_API_KEY:
            st.info("💡 Add GROQ_API_KEY to enable LLM mode")
    
    st.divider()
    
    st.subheader("Security Settings")
    enable_pii_masking = st.checkbox("🔒 Mask PII (Email, Phone, Address)", value=True)
    enable_client_masking = st.checkbox("🏢 Mask Client Names", value=True)
    
    if enable_client_masking:
        known_clients = st.text_area(
            "Known Client Names (one per line)",
            placeholder="Acme Corp\nTech Solutions Inc",
            height=100
        )
        known_clients = [c.strip() for c in known_clients.split('\n') if c.strip()]
    else:
        known_clients = []
    
    st.divider()
    st.subheader("📚 User Guide")
    with st.expander("How to Use"):
        st.markdown("""
        **Single Analysis:**
        1. Upload JD → Analyzes requirements
        2. Upload Resume → Validates against JD
        3. Review detailed report with gaps
        
        **Batch Processing:**
        1. Upload JD
        2. Upload multiple resumes
        3. Compare candidates side-by-side
        
        **Key Features:**
        - ✅ Real vs. Claimed experience
        - ⏱️ Timeline validation
        - 🎯 Interview questions generation
        - 🔒 PII masking
        """)

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Single Analysis",
    "📊 Batch Processing",
    "🔒 Security Audit",
    "❓ Help"
])

# ==================== TAB 1: SINGLE ANALYSIS ====================
with tab1:
    st.header("📝 Single Candidate Analysis")
    
    # JD Upload
    st.subheader("Step 1: Upload Job Description")
    jd_file = st.file_uploader(
        "Upload JD (PDF/DOCX/TXT)",
        type=["pdf", "docx", "txt"],
        key="single_jd"
    )
    
    if jd_file:
        jd_text = extract_text_from_file(jd_file)
        
        if jd_text:
            # Security masking
            if enable_client_masking:
                masker = SecurityMasker()
                jd_masked_result = masker.mask_jd(jd_text, known_clients)
                jd_text = jd_masked_result.masked_text
                
                # Log masking
                audit_entry = create_masking_audit_log(jd_masked_result, "jd")
                st.session_state.masking_audit_log.append(audit_entry)
            
            # Analyze JD
            validator = st.session_state.validator
            jd_summary = validator.jd_analyzer.analyze_jd(jd_text)
            
            st.session_state.jd_summary = jd_summary
            st.session_state.jd_text = jd_text
            
            # Display JD summary
            with st.expander("📋 JD Analysis", expanded=True):
                render_jd_summary(jd_summary)
    
    # Resume Upload
    if st.session_state.jd_text:
        st.divider()
        st.subheader("Step 2: Upload Candidate Resume")
        
        resume_file = st.file_uploader(
            "Upload Resume (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="single_resume"
        )
        
        if resume_file:
            resume_text = extract_text_from_file(resume_file)
            
            if resume_text:
                candidate_name = extract_candidate_name(resume_text)
                
                # Security masking
                if enable_pii_masking:
                    masker = SecurityMasker()
                    resume_masked_result = masker.mask_resume(resume_text)
                    resume_text = resume_masked_result.masked_text
                    
                    # Log masking
                    audit_entry = create_masking_audit_log(resume_masked_result, "resume")
                    st.session_state.masking_audit_log.append(audit_entry)
                
                # Validate candidate
                with st.spinner(f"🔍 Validating {candidate_name}..."):
                    validator = st.session_state.validator
                    report = validator.validate_candidate(
                        jd_text=st.session_state.jd_text,
                        resume_text=resume_text,
                        candidate_name=candidate_name
                    )
                    
                    st.session_state.validation_reports = [report]
                
                st.success("✅ Validation complete!")
                
                # Display report
                st.divider()
                render_validation_report(report)

# ==================== TAB 2: BATCH PROCESSING ====================
with tab2:
    st.header("📊 Batch Candidate Processing")
    
    # JD Upload for batch
    st.subheader("Step 1: Upload Job Description")
    batch_jd_file = st.file_uploader(
        "Upload JD (PDF/DOCX/TXT)",
        type=["pdf", "docx", "txt"],
        key="batch_jd"
    )
    
    batch_jd_text = None
    batch_jd_summary = None
    
    if batch_jd_file:
        batch_jd_text = extract_text_from_file(batch_jd_file)
        
        if batch_jd_text:
            # Security masking
            if enable_client_masking:
                masker = SecurityMasker()
                jd_masked_result = masker.mask_jd(batch_jd_text, known_clients)
                batch_jd_text = jd_masked_result.masked_text
            
            # Analyze JD
            validator = st.session_state.validator
            batch_jd_summary = validator.jd_analyzer.analyze_jd(batch_jd_text)
            
            with st.expander("📋 JD Analysis", expanded=False):
                render_jd_summary(batch_jd_summary)
    
    # Resume uploads
    if batch_jd_text:
        st.divider()
        st.subheader("Step 2: Upload Candidate Resumes")
        
        resume_files = st.file_uploader(
            "Upload Resumes (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="batch_resumes"
        )
        
        if resume_files:
            st.info(f"📊 {len(resume_files)} candidate(s) uploaded")
            
            if st.button("🚀 Process All Candidates", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                batch_reports = []
                validator = st.session_state.validator
                
                for i, resume_file in enumerate(resume_files):
                    status_text.text(f"Processing {resume_file.name}... ({i+1}/{len(resume_files)})")
                    
                    resume_text = extract_text_from_file(resume_file)
                    
                    if resume_text:
                        candidate_name = extract_candidate_name(resume_text)
                        
                        # Security masking
                        if enable_pii_masking:
                            masker = SecurityMasker()
                            resume_masked_result = masker.mask_resume(resume_text)
                            resume_text = resume_masked_result.masked_text
                        
                        # Validate
                        report = validator.validate_candidate(
                            jd_text=batch_jd_text,
                            resume_text=resume_text,
                            candidate_name=candidate_name
                        )
                        
                        batch_reports.append(report)
                    
                    progress_bar.progress((i + 1) / len(resume_files))
                
                status_text.text("✅ Processing complete!")
                
                # Sort by fit score
                batch_reports.sort(key=lambda r: r.overall_fit_score, reverse=True)
                
                st.session_state.batch_reports = batch_reports
                
                st.success(f"✅ Processed {len(batch_reports)} candidates")
    
    # Display batch results
    if st.session_state.batch_reports:
        st.divider()
        st.subheader("📊 Batch Results")
        
        reports = st.session_state.batch_reports
        
        # Summary metrics
        avg_fit = sum(r.overall_fit_score for r in reports) / len(reports)
        strong_fits = len([r for r in reports if r.overall_fit_score >= 75])
        
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total Candidates", len(reports))
        metric_cols[1].metric("Average Fit", f"{avg_fit:.0f}%")
        metric_cols[2].metric("Strong Fits (75%+)", strong_fits)
        metric_cols[3].metric("Top Score", f"{reports[0].overall_fit_score:.0f}%")
        
        st.divider()
        
        # Comparison table
        render_batch_comparison(reports)
        
        st.divider()
        
        # Individual reports
        st.subheader("Individual Reports")
        
        for report in reports:
            icon = "✅" if report.overall_fit_score >= 75 else "⚠️" if report.overall_fit_score >= 60 else "❌"
            with st.expander(f"{icon} {report.candidate_name} - {report.overall_fit_score:.0f}%"):
                render_validation_report(report)

# ==================== TAB 3: SECURITY AUDIT ====================
with tab3:
    st.header("🔒 Security Audit Log")
    
    if st.session_state.masking_audit_log:
        audit_df = pd.DataFrame(st.session_state.masking_audit_log)
        st.dataframe(audit_df, use_container_width=True)
        
        st.divider()
        st.download_button(
            label="📥 Export Audit Log (CSV)",
            data=audit_df.to_csv(index=False),
            file_name=f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No masking operations performed yet")

# ==================== TAB 4: HELP ====================
with tab4:
    st.header("❓ Help & Documentation")
    
    st.markdown("""
    ## What's New in v3.0
    
    ### 🎯 Enhanced Validation
    - **Real vs. Claimed Experience**: Distinguishes actual project work from skill lists
    - **Timeline Analysis**: Detects resume padding (claimed 8 years but only 2 years validated)
    - **Evidence-Based Scoring**: Each skill validated with project evidence
    
    ### 📊 Output Format
    
    **For Each Candidate You Get:**
    
    1. **Fit Score** (0-100)
       - Based on mandatory skills coverage
       - Quality of project evidence  
       - Experience timeline authenticity
    
    2. **Validated Skills** (✅ Real Project Work)
       - Skills with concrete project evidence
       - Measurable outcomes
       - Evidence strength score
    
    3. **Weak Skills** (⚠️ Claimed Only)
       - Listed but no project evidence
       - Auto-generated interview questions
       - Suggestions for validation
    
    4. **Timeline Analysis** (⏱️)
       - Total years claimed vs. validated
       - Experience breakdown by type
       - Red flags for padding
    
    5. **Critical Gaps** (❌)
       - Missing mandatory skills
       - Improvement areas
    
    ### 🔍 Understanding Scores
    
    **Experience Types:**
    - **Real Project**: Action verbs + outcomes + metrics (Score: 60-100%)
    - **Claimed Knowledge**: Mentioned but no evidence (Score: 20-59%)
    - **Missing**: Not found in resume (Score: 0%)
    
    **Validation Ratios:**
    - **>70%**: Strong - Most experience validated
    - **40-70%**: Moderate - Mixed experience
    - **<40%**: Red Flag - Possible padding
    
    ### 🎯 Best Practices
    
    1. **Review project evidence** - Don't rely solely on scores
    2. **Check timeline validation** - Spot experience inflation
    3. **Use interview questions** - Validate weak skills
    4. **Compare candidates** - Side-by-side in batch mode
    5. **Export reports** - Share with hiring managers
    
    ### 🔒 Security Features
    
    - **PII Masking**: Removes emails, phones, addresses
    - **Client Masking**: Protects client names and codes
    - **Audit Logging**: Track all masking operations
    - **No Data Storage**: All processing in-memory
    
    ### 📥 Export Options
    
    - **Markdown Reports**: Full validation details
    - **CSV Summaries**: Quick comparison data
    - **Batch Exports**: All candidates at once
    
    """)

# Footer
st.divider()
st.caption("🎯 JobFit Analyzer v3.0 | Deep Semantic Validation | 🔒 PII Protected")
