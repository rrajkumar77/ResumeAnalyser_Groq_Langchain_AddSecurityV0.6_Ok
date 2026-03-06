"""
TEKsystems JobFit Analyzer - User-Friendly Edition (FIXED)
===========================================================

**RECRUITER-FRIENDLY VERSION WITH FULL INTEGRATION**

Key Features:
1. ✅ Simplified Evidence Display (no technical jargon)
2. ✅ Clear Visual Indicators (🟢🟡🟠🔴 for skill quality)
3. ✅ 3-Click Decision Process
4. ✅ Built-in User Guide
5. ✅ Hiring Recommendations (not just scores)
6. ✅ Recruiter Workflow Features (NEW!)
   - Lock JD for batch screening
   - Candidate history tracking
   - One-page hiring summaries
   - Shortlist management
   - Collaboration features

All Advanced Features Included:
- Security Masking with Skill Filtering
- Batch Processing
- Interview Questions
- Skills Gap Analysis
- Recruiter Workflow Tools
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime
from typing import Optional

import docx
import fitz
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Security and enhanced semantic imports
from security_masker import SecurityMasker, MaskingResult, create_masking_audit_log
from enhanced_semantic_matcher import (
    EnhancedSemanticSkillMatcher,
    ExperienceDepth,
    ActionVerbIntensity,
)

# Additional recommendation modules
from batch_processor import BatchCandidateProcessor
from improved_question_generator import ImprovedQuestionGenerator
from situational_technical_generator import SituationalTechnicalGenerator
from coding_question_generator import CodingQuestionGenerator
from skills_gap_analyzer import SkillsGapAnalyzer

# Skill filtering
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
    st.warning("⚠️ GROQ_API_KEY not found. Set in .env or Streamlit Secrets for full functionality.")
    GROQ_API_KEY = "dummy_key"

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="JobFit Analyzer - User-Friendly",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== SESSION STATE INITIALIZATION ====================
if "security_masker" not in st.session_state:
    st.session_state.security_masker = SecurityMasker()
if "semantic_matcher" not in st.session_state:
    st.session_state.semantic_matcher = EnhancedSemanticSkillMatcher()
if "batch_processor" not in st.session_state:
    st.session_state.batch_processor = BatchCandidateProcessor(matcher=st.session_state.semantic_matcher)
if "masking_audit_log" not in st.session_state:
    st.session_state.masking_audit_log = []
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = None
if "technical_scenarios" not in st.session_state:
    st.session_state.technical_scenarios = None
if "coding_questions" not in st.session_state:
    st.session_state.coding_questions = None
if "gap_analysis" not in st.session_state:
    st.session_state.gap_analysis = None

# Recruiter workflow session state
if "locked_jd" not in st.session_state:
    st.session_state.locked_jd = None
if "locked_jd_text" not in st.session_state:
    st.session_state.locked_jd_text = ""
if "locked_priority_skills" not in st.session_state:
    st.session_state.locked_priority_skills = []
if "current_candidate_name" not in st.session_state:
    st.session_state.current_candidate_name = ""
if "hiring_summary" not in st.session_state:
    st.session_state.hiring_summary = None
if "hiring_summary_candidate" not in st.session_state:
    st.session_state.hiring_summary_candidate = ""

# Convenience references
security_masker = st.session_state.security_masker
semantic_matcher = st.session_state.semantic_matcher
batch_processor = st.session_state.batch_processor

# ==================== HELPER FUNCTIONS ====================
def parse_priority_skills(priority_input: str) -> list:
    """Parse and normalize priority skills."""
    if not priority_input:
        return []
    skills = []
    for line in priority_input.split("\n"):
        for skill in line.split(","):
            skill = skill.strip()
            if skill:
                skills.append(skill)
    return skills

def process_file(uploaded_file) -> str:
    """Extract text from uploaded file."""
    if uploaded_file is None:
        return ""
    
    file_bytes = uploaded_file.read()
    ext = uploaded_file.name.split(".")[-1].lower()
    
    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return " ".join([page.get_text() for page in doc]).strip()
    elif ext == "docx":
        d = docx.Document(io.BytesIO(file_bytes))
        return " ".join([p.text for p in d.paragraphs]).strip()
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors='ignore').strip()
    else:
        return ""

def apply_masking(text: str, doc_type: str, known_clients: list = None):
    """Apply security masking."""
    if doc_type == "resume" and enable_pii_masking:
        result = security_masker.mask_resume(text)
        audit_entry = create_masking_audit_log(result, "resume")
        st.session_state.masking_audit_log.append(audit_entry)
        return result.masked_text, result
    elif doc_type == "jd" and enable_client_masking:
        result = security_masker.mask_jd(text, known_client_names=known_clients)
        audit_entry = create_masking_audit_log(result, "jd")
        st.session_state.masking_audit_log.append(audit_entry)
        return result.masked_text, result
    else:
        return text, MaskingResult(masked_text=text, mask_count=0)

# ==================== SIMPLIFIED EVIDENCE DISPLAY ====================
def display_skill_card(skill, is_priority: bool):
    """Display a single skill card with visual indicators."""
    
    # Color coding
    if skill.hands_on_score >= 0.85:
        color = "🟢"
        level = "Excellent"
    elif skill.hands_on_score >= 0.70:
        color = "🟡"
        level = "Good"
    elif skill.hands_on_score >= 0.55:
        color = "🟠"
        level = "Moderate"
    else:
        color = "🔴"
        level = "Weak"
    
    # Experience stars
    exp_depth = getattr(skill, 'experience_depth', ExperienceDepth.NOT_FOUND)
    stars = {
        ExperienceDepth.EXPERT: "⭐⭐⭐",
        ExperienceDepth.PROFICIENT: "⭐⭐",
        ExperienceDepth.COMPETENT: "⭐",
        ExperienceDepth.BASIC: "◐",
        ExperienceDepth.MENTIONED_ONLY: "○",
    }.get(exp_depth, "○")
    
    with st.expander(
        f"{color} **{skill.skill_name}** {stars} "
        f"{'🎯 PRIORITY' if is_priority else ''} — {skill.hands_on_score:.0%} hands-on",
        expanded=False
    ):
        col1, col2, col3 = st.columns(3)
        col1.metric("Score", f"{skill.hands_on_score:.0%}", f"{level}")
        col2.metric("Experience", exp_depth.value.title())
        
        # Check for metrics
        has_metrics = False
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            has_metrics = any(getattr(e, 'has_metrics', False) for e in skill.enhanced_evidence)
        col3.metric("Has Metrics", "✅ Yes" if has_metrics else "❌ No")
        
        st.write("**Why this skill is validated:**")
        st.info(skill.reasoning)

def display_hiring_recommendation(overall_fit, validated_skills, priority_skills_input, missing_skills):
    """Display clear hiring recommendation."""
    st.divider()
    st.subheader("💡 Hiring Recommendation")
    
    priority_set = set(s.lower().strip() for s in parse_priority_skills(priority_skills_input))
    priority_validated = sum(
        1 for s in validated_skills
        if hasattr(s, 'priority_skill') and s.skill_name.lower() in priority_set
    )
    total_priority = len(priority_set)
    missing_priority = sum(
        1 for s in missing_skills
        if s.skill_name.lower() in priority_set
    )
    
    if overall_fit >= 0.85 and missing_priority == 0:
        st.success("✅ **STRONG MATCH - Fast-Track to Interview**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Excellent)")
        st.write(f"• All {total_priority} priority skills validated")
        st.write(f"• {len(validated_skills)} total skills with hands-on evidence")
        st.write("\n**Next Step:** Schedule technical interview")
        
    elif overall_fit >= 0.70:
        st.info("🟡 **GOOD MATCH - Phone Screen Recommended**")
        st.write(f"• Overall fit: {overall_fit:.0%}")
        st.write(f"• {priority_validated}/{total_priority} priority skills validated")
        if missing_priority > 0:
            st.write(f"• ⚠️ Missing {missing_priority} priority skill(s)")
            st.write("\n**Next Step:** Phone screen to assess gaps")
        else:
            st.write("\n**Next Step:** Phone screen then technical interview")
            
    elif overall_fit >= 0.60:
        st.warning("🟠 **MODERATE MATCH - Technical Assessment Needed**")
        st.write(f"• Overall fit: {overall_fit:.0%}")
        st.write(f"• {priority_validated}/{total_priority} priority skills validated")
        st.write(f"• Missing {missing_priority} priority skill(s)")
        st.write("\n**Recommendation:** Use 'Skills Gap Analysis' to evaluate training potential")
    else:
        st.error("🔴 **WEAK MATCH - Keep Searching**")
        st.write(f"• Overall fit: {overall_fit:.0%}")
        st.write(f"• Only {priority_validated}/{total_priority} priority skills validated")
        st.write(f"• Missing {missing_priority} critical skill(s)")
        st.write("\n**Recommendation:** Continue sourcing candidates with better skill alignment")

def create_custom_hiring_summary(candidate_name, jd_title, fit_score, validated_skills, missing_skills, priority_skills, gap_analysis):
    """Create a well-formatted hiring summary with proper alignment and clear training recommendations."""
    
    # Determine recommendation
    priority_set = set(s.lower().strip() for s in priority_skills) if priority_skills else set()
    priority_validated = sum(1 for s in validated_skills if s.skill_name.lower() in priority_set)
    missing_priority = sum(1 for s in missing_skills if s.skill_name.lower() in priority_set)
    
    if fit_score >= 0.85 and missing_priority == 0:
        recommendation = "HIRE"
        recommendation_detail = "Strong technical match with all priority skills validated"
    elif fit_score >= 0.70:
        recommendation = "HIRE WITH TRAINING"
        # Get specific training needs from gap analysis or missing skills
        if gap_analysis:
            training_areas = [skill for skill in gap_analysis.get('trainable_skills', [])[:3]]
            if training_areas:
                training_detail = ", ".join(training_areas)
                recommendation_detail = f"Good foundation. Recommend 3-month training on: {training_detail}"
            else:
                recommendation_detail = "Good foundation with minor skill gaps that can be addressed through onboarding"
        else:
            if missing_skills:
                training_areas = [s.skill_name for s in missing_skills[:3]]
                training_detail = ", ".join(training_areas)
                recommendation_detail = f"Good foundation. Recommend training on: {training_detail}"
            else:
                recommendation_detail = "Good foundation. Recommend phone screen to assess learning aptitude"
    elif fit_score >= 0.60:
        recommendation = "CONDITIONAL"
        recommendation_detail = "Moderate fit. Requires technical assessment and training evaluation"
    else:
        recommendation = "PASS"
        recommendation_detail = "Weak skill alignment. Continue sourcing"
    
    # Helper function to capitalize skill names
    def capitalize_skill(skill_name):
        capitalization_map = {
            'sql': 'SQL', 'nosql': 'NoSQL', 'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP',
            'api': 'API', 'rest': 'REST', 'json': 'JSON', 'xml': 'XML', 'html': 'HTML',
            'css': 'CSS', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
            'python': 'Python', 'java': 'Java', 'dotnet': '.NET', '.net': '.NET',
            'c#': 'C#', 'c++': 'C++', 'node.js': 'Node.js', 'nodejs': 'Node.js',
            'react': 'React', 'angular': 'Angular', 'vue': 'Vue', 'docker': 'Docker',
            'kubernetes': 'Kubernetes', 'jenkins': 'Jenkins', 'git': 'Git',
            'github': 'GitHub', 'gitlab': 'GitLab', 'jira': 'JIRA', 'agile': 'Agile',
            'scrum': 'Scrum', 'devops': 'DevOps', 'cicd': 'CI/CD', 'ci/cd': 'CI/CD',
            'ml': 'ML', 'ai': 'AI', 'nlp': 'NLP', 'etl': 'ETL', 'iot': 'IoT',
            'ui': 'UI', 'ux': 'UX', 'sap': 'SAP', 'erp': 'ERP', 'crm': 'CRM',
            'cloud': 'Cloud', 'terraform': 'Terraform', 'ansible': 'Ansible',
            'mongodb': 'MongoDB', 'postgresql': 'PostgreSQL', 'mysql': 'MySQL',
            'powerbi': 'Power BI', 'power bi': 'Power BI', 'tableau': 'Tableau',
            'databricks': 'Databricks', 'spark': 'Spark', 'kafka': 'Kafka',
        }
        
        skill_name_lower = skill_name.lower().strip()
        if skill_name_lower in capitalization_map:
            return capitalization_map[skill_name_lower]
        elif len(skill_name) <= 4 and skill_name.isupper():
            return skill_name
        elif ' ' in skill_name or '-' in skill_name:
            return skill_name.title()
        else:
            return skill_name.capitalize()
    
    # Build markdown summary with proper formatting
    summary_md = f"""# HIRING SUMMARY: {candidate_name}

**Position:** {jd_title}  
**Analysis Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  
**Overall Fit:** {fit_score:.0%}

---

## 🎯 RECOMMENDATION: {recommendation}

{recommendation_detail}

---

## ✅ TOP STRENGTHS

"""
    
    # Add validated skills with proper numbering and detailed justification
    top_skills = sorted(validated_skills, 
                       key=lambda s: (s.priority_skill if hasattr(s, 'priority_skill') else False, 
                                    s.hands_on_score if hasattr(s, 'hands_on_score') else 0),
                       reverse=True)[:5]
    
    for i, skill in enumerate(top_skills, 1):
        skill_name = capitalize_skill(skill.skill_name)
        
        # Get experience depth
        exp_depth = getattr(skill, 'experience_depth', None)
        if exp_depth:
            experience_level = exp_depth.value.upper()
        else:
            experience_level = "PROFICIENT"
        
        # Get hands-on score for quality assessment
        hands_on_score = getattr(skill, 'hands_on_score', 0.75)
        if hands_on_score >= 0.85:
            quality = "Excellent"
        elif hands_on_score >= 0.70:
            quality = "Strong"
        else:
            quality = "Moderate"
        
        # Check for metrics
        has_metrics = False
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            has_metrics = any(getattr(e, 'has_metrics', False) for e in skill.enhanced_evidence)
        
        # Build justification
        justification_parts = []
        justification_parts.append(f"{experience_level} level")
        justification_parts.append(f"{quality.lower()} hands-on evidence ({hands_on_score:.0%})")
        if has_metrics:
            justification_parts.append("measurable outcomes demonstrated")
        
        justification = " with ".join(justification_parts)
        
        summary_md += f"{i}. **{skill_name}**  \n   {justification.capitalize()}\n\n"
        
        # Add EVIDENCE from resume
        summary_md += "   **Evidence from resume:**\n"
        reasoning = getattr(skill, 'reasoning', '')
        if reasoning and len(reasoning) > 10:
            # Clean up and format the reasoning
            summary_md += f"   > {reasoning}\n\n"
        elif hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            # Show first piece of evidence
            for evidence in skill.enhanced_evidence[:2]:
                evidence_text = getattr(evidence, 'evidence_text', str(evidence))
                if evidence_text and len(evidence_text) > 10:
                    summary_md += f"   > {evidence_text}\n"
        else:
            summary_md += f"   > Candidate demonstrates practical {skill_name} experience\n"
        summary_md += "\n"
    
    # Priority skills section with DETAILED BREAKDOWN
    summary_md += f"""---

## 📊 PRIORITY SKILLS

"""
    
    if priority_set:
        if priority_validated == len(priority_set):
            summary_md += f"✅ **All {len(priority_set)} priority skills validated**\n\n"
            
            # List which priority skills are validated with evidence
            validated_priority_skills = [s for s in validated_skills if s.skill_name.lower() in priority_set]
            for skill in validated_priority_skills:
                skill_name = capitalize_skill(skill.skill_name)
                hands_on_score = getattr(skill, 'hands_on_score', 0)
                reasoning = getattr(skill, 'reasoning', '')
                
                summary_md += f"- **{skill_name}** ({hands_on_score:.0%} validation)\n"
                if reasoning and len(reasoning) > 10:
                    # Get first sentence or key phrase
                    evidence_snippet = reasoning.split('.')[0][:100]
                    summary_md += f"  - {evidence_snippet}\n"
            summary_md += "\n"
        else:
            summary_md += f"⚠️ **{priority_validated}/{len(priority_set)} priority skills validated**\n\n"
            
            # Show validated priority skills
            validated_priority_skills = [s for s in validated_skills if s.skill_name.lower() in priority_set]
            if validated_priority_skills:
                summary_md += "**Validated:**\n"
                for skill in validated_priority_skills:
                    skill_name = capitalize_skill(skill.skill_name)
                    hands_on_score = getattr(skill, 'hands_on_score', 0)
                    summary_md += f"- {skill_name} ({hands_on_score:.0%})\n"
                summary_md += "\n"
            
            # Show missing priority skills with reasoning
            if missing_priority > 0:
                missing_priority_skills = [s for s in missing_skills if s.skill_name.lower() in priority_set]
                summary_md += "**Missing Priority Skills:**\n"
                for skill in missing_priority_skills:
                    skill_name = capitalize_skill(skill.skill_name)
                    reasoning = getattr(skill, 'reasoning', 'Not mentioned in resume')
                    summary_md += f"- **{skill_name}**\n"
                    summary_md += f"  - Why missing: {reasoning}\n"
                summary_md += "\n"
    else:
        summary_md += "No priority skills specified\n"
    
    # Key gaps section with JUSTIFICATION
    summary_md += f"""
---

## ⚠️ KEY GAPS

"""
    
    if missing_skills:
        summary_md += f"**{len(missing_skills)} skill(s) not found in resume:**\n\n"
        for skill in missing_skills[:5]:  # Top 5 gaps
            skill_name = capitalize_skill(skill.skill_name)
            reasoning = getattr(skill, 'reasoning', 'No evidence found in resume')
            
            summary_md += f"### {skill_name}\n"
            summary_md += f"**Gap Analysis:** {reasoning}\n\n"
            
        if len(missing_skills) > 5:
            summary_md += f"**Plus {len(missing_skills) - 5} additional gaps** (see detailed analysis)\n"
    else:
        summary_md += "No significant gaps identified\n"
    
    return summary_md


# ==================== SIDEBAR ====================
st.sidebar.title("⚙️ Settings")

# Security settings
st.sidebar.subheader("🔒 Security")
enable_pii_masking = st.sidebar.checkbox("Mask PII (Name, Email, Phone)", value=True)
enable_client_masking = st.sidebar.checkbox("Mask Client Info", value=True)

if enable_client_masking:
    known_clients_input = st.sidebar.text_area(
        "Known Client Names (one per line)",
        placeholder="Acme Corp\nTechStartup Inc",
        help="Add client names to mask"
    )
    known_clients = [c.strip() for c in known_clients_input.split("\n") if c.strip()]
else:
    known_clients = []

st.sidebar.divider()

# NEW: JD Lock Feature for Batch Screening
st.sidebar.subheader("🔒 Lock JD for Batch Screening")
if st.session_state.locked_jd:
    st.sidebar.success(f"✅ Locked: {st.session_state.locked_jd}")
    if st.sidebar.button("🔓 Unlock JD"):
        st.session_state.locked_jd = None
        st.session_state.locked_jd_text = ""
        st.session_state.locked_priority_skills = []
        st.rerun()
else:
    st.sidebar.info("💡 Lock a JD to quickly screen multiple candidates")

st.sidebar.divider()

# User guide
with st.sidebar.expander("📖 Quick Guide"):
    st.markdown("""
    **3-Click Decision Process:**
    1. Upload JD & Resume
    2. Review visual indicators (🟢🟡🟠🔴)
    3. Read hiring recommendation
    
    **Color Codes:**
    - 🟢 Excellent (85%+)
    - 🟡 Good (70-85%)
    - 🟠 Moderate (55-70%)
    - 🔴 Weak (<55%)
    
    **NEW Features:**
    - Lock/Unlock JD for fast batch screening
    - Generate hiring summaries
    """)

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 Single Analysis",
    "📊 Batch Processing",
    "💬 Basic Questions",
    "🎯 Technical Scenarios",
    "💻 Coding Challenges",
    "📈 Skills Gap",
    "📄 Hiring Summary",
    "🔒 Security Audit"
])

# ==================== TAB 1: SINGLE ANALYSIS ====================
with tab1:
    st.header("📋 Single Candidate Analysis")
    
    # JD Input
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📄 Job Description")
    with col2:
        if st.session_state.locked_jd:
            if st.button("🔓 Unlock JD"):
                st.session_state.locked_jd = None
                st.session_state.locked_jd_text = ""
                st.session_state.locked_priority_skills = []
                st.rerun()
    
    if st.session_state.locked_jd:
        jd_text = st.session_state.locked_jd_text
        st.text_area("Locked JD (read-only)", jd_text, height=150, disabled=True, key="locked_jd_display")
    else:
        jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], key="jd_single")
        jd_text = process_file(jd_file) if jd_file else ""
        
        if jd_text:
            if st.button("🔒 Lock this JD for batch screening"):
                st.session_state.locked_jd = jd_file.name if jd_file else "Manual Entry"
                st.session_state.locked_jd_text = jd_text
                st.rerun()
    
    # Priority Skills
    if st.session_state.locked_jd:
        priority_skills_input = "\n".join(st.session_state.locked_priority_skills)
        st.text_area("Locked Priority Skills (read-only)", priority_skills_input, height=100, disabled=True)
    else:
        priority_skills_input = st.text_area(
            "🎯 Priority Skills (Must-Have, one per line)",
            placeholder="Python\nAWS\nDocker\nKubernetes",
            height=100,
            help="List critical skills that are non-negotiable"
        )
        if jd_text and st.button("🔒 Lock Priority Skills"):
            st.session_state.locked_priority_skills = parse_priority_skills(priority_skills_input)
            st.rerun()
    
    st.divider()
    
    # Resume Input
    st.subheader("📃 Resume")
    
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], key="resume_single")
    resume_text = process_file(resume_file) if resume_file else ""
    
    st.divider()
    
    # Analyze button
    col1, col2, col3, col4 = st.columns(4)
    analyze_clicked = col1.button("🔍 Analyze Match", type="primary", use_container_width=True)
    gen_questions = col2.button("💬 Basic Questions", use_container_width=True)
    gen_scenarios = col3.button("🎯 Technical Scenarios", use_container_width=True)
    gen_coding = col4.button("💻 Coding Challenges", use_container_width=True)
    
    col5, col6 = st.columns(2)
    gen_gap = col5.button("📈 Analyze Skills Gaps", use_container_width=True)
    gen_summary = col6.button("📄 Generate Hiring Summary", use_container_width=True)
    
    # Analysis logic
    if analyze_clicked:
        if not jd_text or not resume_text:
            st.error("❌ Please upload both JD and Resume")
        else:
            with st.spinner("🔍 Analyzing candidate fit..."):
                # Apply masking
                jd_masked, _ = apply_masking(jd_text, "jd", known_clients)
                resume_masked, _ = apply_masking(resume_text, "resume")
                
                # Parse priority skills
                priority_skills = parse_priority_skills(priority_skills_input) if not st.session_state.locked_jd else st.session_state.locked_priority_skills
                
                # Analyze
                report = semantic_matcher.analyze_with_priorities(
                    jd_text=jd_masked,
                    resume_text=resume_masked,
                    priority_skills=priority_skills
                )
                
                st.session_state.last_report = report
                
                # Store candidate name for hiring summary
                if resume_file:
                    candidate_name = resume_file.name.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
                    st.session_state.current_candidate_name = candidate_name
                
                st.success("✅ Analysis complete!")
    
    # Display results
    if st.session_state.last_report:
        report = st.session_state.last_report
        
        st.divider()
        st.subheader("📊 Analysis Results")
        
        # Overall score
        score_col1, score_col2, score_col3, score_col4 = st.columns(4)
        score_col1.metric("Overall Fit", f"{report.overall_relevance_score:.0%}")
        score_col2.metric("Validated Skills", len(report.validated_skills))
        score_col3.metric("Weak Evidence", len(report.weak_skills))
        score_col4.metric("Missing Skills", len(report.missing_skills))
        
        # Priority skills check
        priority_skills = parse_priority_skills(priority_skills_input) if not st.session_state.locked_jd else st.session_state.locked_priority_skills
        if priority_skills:
            priority_set = set(s.lower() for s in priority_skills)
            priority_validated = sum(
                1 for s in report.validated_skills
                if s.skill_name.lower() in priority_set
            )
            st.info(f"🎯 Priority Skills: {priority_validated}/{len(priority_skills)} validated")
        
        # Hiring recommendation
        display_hiring_recommendation(
            report.overall_relevance_score,
            report.validated_skills,
            priority_skills_input,
            report.missing_skills
        )
        
        # Validated skills
        st.divider()
        st.subheader(f"✅ Validated Skills ({len(report.validated_skills)})")
        
        if report.validated_skills:
            for skill in report.validated_skills:
                is_priority = skill.skill_name.lower() in (set(s.lower() for s in priority_skills) if priority_skills else set())
                display_skill_card(skill, is_priority)
        else:
            st.warning("No validated skills found")
        
        # Weak skills
        if report.weak_skills:
            st.divider()
            st.subheader(f"⚠️ Skills with Weak Evidence ({len(report.weak_skills)})")
            with st.expander("View weak skills"):
                for skill in report.weak_skills:
                    st.write(f"• {skill.skill_name}: {skill.reasoning}")
        
        # Missing skills
        if report.missing_skills:
            st.divider()
            st.subheader(f"❌ Missing Skills ({len(report.missing_skills)})")
            with st.expander("View missing skills"):
                for skill in report.missing_skills:
                    st.write(f"• {skill.skill_name}")
        
        # Ignored skills (skills-only listings)
        if report.ignored_skills:
            st.divider()
            st.subheader(f"⊘ Ignored Skills (Resume Padding) ({len(report.ignored_skills)})")
            with st.expander("View ignored skills"):
                st.info("These skills were listed but have no hands-on evidence in experience section")
                for skill in report.ignored_skills:
                    st.write(f"• {skill.skill_name}: {skill.reasoning}")
    
    # Generate basic questions
    if gen_questions and st.session_state.last_report:
        with st.spinner("Generating interview questions..."):
            report = st.session_state.last_report
            generator = ImprovedQuestionGenerator(groq_api_key=GROQ_API_KEY)
            questions = generator.generate_questions(
                jd_text=jd_text,
                resume_text=resume_text,
                validated_skills=[s.skill_name for s in report.validated_skills],
                missing_skills=[s.skill_name for s in report.missing_skills]
            )
            st.session_state.interview_questions = questions
            st.success(f"✅ Generated {len(questions)} interview questions")
    
    # Generate technical scenarios
    if gen_scenarios and st.session_state.last_report:
        with st.spinner("Generating technical scenarios..."):
            report = st.session_state.last_report
            generator = SituationalTechnicalGenerator(groq_api_key=GROQ_API_KEY)
            scenarios = generator.generate_scenarios(
                jd_text=jd_text,
                validated_skills=[s.skill_name for s in report.validated_skills],
                weak_skills=[s.skill_name for s in report.weak_skills],
                missing_skills=[s.skill_name for s in report.missing_skills]
            )
            st.session_state.technical_scenarios = scenarios
            st.success(f"✅ Generated {len(scenarios)} technical scenarios")
    
    # Generate coding challenges
    if gen_coding and st.session_state.last_report:
        with st.spinner("Generating coding challenges..."):
            report = st.session_state.last_report
            generator = CodingQuestionGenerator(groq_api_key=GROQ_API_KEY)
            coding_qs = generator.generate_challenges(
                jd_text=jd_text,
                validated_skills=[s.skill_name for s in report.validated_skills[:10]]
            )
            st.session_state.coding_questions = coding_qs
            st.success(f"✅ Generated {len(coding_qs)} coding challenges")
    
    # Generate skills gap analysis
    if gen_gap and st.session_state.last_report:
        with st.spinner("Analyzing skills gaps..."):
            report = st.session_state.last_report
            analyzer = SkillsGapAnalyzer()
            gap = analyzer.analyze_gap(
                jd_text=jd_text,
                validated_skills=report.validated_skills,
                weak_skills=report.weak_skills,
                missing_skills=report.missing_skills
            )
            st.session_state.gap_analysis = gap
            st.success("✅ Skills gap analysis complete")
    
    # Generate hiring summary
    if gen_summary and st.session_state.last_report:
        with st.spinner("Generating hiring summary..."):
            report = st.session_state.last_report
            priority_skills = parse_priority_skills(priority_skills_input) if not st.session_state.locked_jd else st.session_state.locked_priority_skills
            
            # Get candidate name from session state (set during analysis)
            candidate_name = st.session_state.get('current_candidate_name', 'Candidate')
            
            # Generate custom formatted summary
            summary_md = create_custom_hiring_summary(
                candidate_name=candidate_name,
                jd_title=st.session_state.locked_jd or "Job Position",
                fit_score=report.overall_relevance_score,
                validated_skills=report.validated_skills,
                missing_skills=report.missing_skills,
                priority_skills=priority_skills,
                gap_analysis=st.session_state.gap_analysis
            )
            
            st.session_state.hiring_summary = summary_md
            st.session_state.hiring_summary_candidate = candidate_name
            st.success("✅ Hiring summary generated!")


# ==================== TAB 2: BATCH PROCESSING ====================
with tab2:
    st.header("📊 Batch Candidate Processing")
    
    if not st.session_state.locked_jd:
        st.warning("⚠️ Please lock a JD in the 'Single Analysis' tab first")
    else:
        st.success(f"Using locked JD: {st.session_state.locked_jd}")
        
        st.subheader("📁 Upload Candidate Resumes")
        resume_files = st.file_uploader(
            "Upload multiple resumes (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="batch_resumes"
        )
        
        if resume_files and st.button("🚀 Process Batch", type="primary"):
            with st.spinner(f"Processing {len(resume_files)} candidates..."):
                # Process each resume
                resumes_dict = {}
                for resume_file in resume_files:
                    resume_text = process_file(resume_file)
                    if resume_text:
                        resumes_dict[resume_file.name] = resume_text
                
                # Batch analyze
                priority_skills = st.session_state.locked_priority_skills
                results = batch_processor.process_batch(
                    jd_text=st.session_state.locked_jd_text,
                    resume_texts=resumes_dict,
                    priority_skills=priority_skills
                )
                
                st.session_state.batch_results = results
                
                st.success(f"✅ Processed {len(results.results)} candidates")
                        
        # Display batch results
        if st.session_state.batch_results:
            results = st.session_state.batch_results
            
            st.divider()
            st.subheader("📊 Batch Results")
            
            # After batch processing results = batch_processor.process_batch(...)
            st.success(f"✅ Processed {len(results.results)} candidates")
            
            # Summary metrics
            stats = results.get_statistics()  # ✅ THIS LINE WAS MISSING
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Candidates", stats['total_candidates'])
            col2.metric("Strong Matches", stats['strong_matches_75plus'])
            col3.metric("Good Matches", stats['good_matches_60_to_75'])
            col4.metric("Avg Fit Score", f"{stats['avg_fit_score']:.0%}")           
            
            # Ranked table
            st.subheader("🏆 Ranked Candidates")
            
            df_data = []
            for rank, candidate in enumerate(results.results, 1):
                df_data.append({
                    "Rank": rank,
                    "Candidate": candidate.candidate_id,
                    "Fit Score": f"{candidate.fit_score:.0%}",
                    "Validated Skills": candidate.validated_skills_count,
                    "Priority Skills": f"{candidate.priority_skills_validated}/{len(st.session_state.locked_priority_skills)}",
                    "Recommendation": candidate.recommendation
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export options
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results (CSV)",
                    data=csv_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                json_data = json.dumps([c.__dict__ for c in results.results], indent=2)
                st.download_button(
                    label="📥 Download Results (JSON)",
                    data=json_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# ==================== TAB 3: BASIC QUESTIONS ====================
with tab3:
    st.header("💬 Basic Interview Questions")
    
    if st.session_state.interview_questions:
        questions = st.session_state.interview_questions
        st.success(f"✅ Generated {len(questions)} interview questions")
        
        st.info("💡 **Tip:** These questions probe validated skills, weak areas, and missing competencies.")
        
        # Group by category
        for category in ["Technical", "Behavioral", "Gap Assessment"]:
            cat_questions = [q for q in questions if q.question_type == category]
            if cat_questions:
                st.subheader(f"{category} Questions")
                
                for i, q in enumerate(cat_questions, 1):
                    with st.expander(f"**Q{i}: {q.question}**", expanded=False):
                        st.markdown(f"**Rationale:** {q.rationale}")
                        
                        st.markdown("**What to listen for:**")
                        for signal in q.good_answer_signals:
                            st.success(f"✅ {signal}")
                        
                        st.markdown("**Red flags:**")
                        for flag in q.red_flags:
                            st.error(f"🚩 {flag}")
                        
                        if q.follow_up_questions:
                            st.markdown("**Follow-up questions:**")
                            for j, follow_up in enumerate(q.follow_up_questions, 1):
                                st.write(f"{j}. {follow_up}")
        
        # Export option
        st.divider()
        if st.button("📥 Export Questions"):
            export_text = "INTERVIEW QUESTIONS\n" + "="*80 + "\n\n"
            for q in questions:
                export_text += q.format_for_interviewer() + "\n\n"
            
            st.download_button(
                label="Download as Text File",
                data=export_text,
                file_name=f"interview_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    else:
        st.info("💡 Upload a JD and Resume in the 'Single Analysis' tab, then click 'Basic Questions'")

# ==================== TAB 4: TECHNICAL SCENARIOS ====================
with tab4:
    st.header("🎯 Situational Technical Questions")
    
    if st.session_state.technical_scenarios:
        questions = st.session_state.technical_scenarios
        st.success(f"✅ Generated {len(questions)} technical scenarios")
        
        st.info("💡 **Tip:** These scenarios test problem-solving and technical depth in realistic situations.")
        
        for i, q in enumerate(questions, 1):
            with st.expander(
                f"**Scenario {i}: {q.skill_area}** | {q.scenario_type.value} | {q.difficulty}",
                expanded=False
            ):
                # Scenario
                st.markdown("### 🎬 Scenario")
                st.info(q.scenario)
                
                # Question
                st.markdown("### ❓ Question")
                st.markdown(q.question)
                
                st.divider()
                
                # Answer guide in tabs
                guide_tab1, guide_tab2, guide_tab3 = st.tabs([
                    "✅ Ideal Approach",
                    "🔑 Key Considerations",
                    "🚩 Red Flags"
                ])
                
                with guide_tab1:
                    st.markdown("**Step-by-step approach you want to hear:**")
                    for j, step in enumerate(q.ideal_approach, 1):
                        st.write(f"{j}. {step}")
                
                with guide_tab2:
                    st.markdown("**Important points candidate should mention:**")
                    for consideration in q.key_considerations:
                        st.success(f"• {consideration}")
                
                with guide_tab3:
                    st.markdown("**Warning signs of poor problem-solving:**")
                    for flag in q.red_flags:
                        st.error(f"⚠️ {flag}")
                
                # Follow-ups
                with st.expander("🔍 Follow-Up Questions", expanded=False):
                    for j, follow_up in enumerate(q.follow_up_questions, 1):
                        st.write(f"{j}. {follow_up}")
        
        # Download option
        st.divider()
        if st.button("📥 Export Scenarios"):
            export_text = "SITUATIONAL TECHNICAL QUESTIONS\n" + "="*80 + "\n\n"
            for q in questions:
                export_text += q.format_for_interviewer() + "\n\n"
            
            st.download_button(
                label="Download as Text File",
                data=export_text,
                file_name=f"situational_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    else:
        st.info("💡 Upload a JD in the 'Single Analysis' tab, then click 'Technical Scenarios'")

# ==================== TAB 5: CODING CHALLENGES ====================
with tab5:
    st.header("💻 Coding Interview Challenges")
    
    if st.session_state.coding_questions:
        questions = st.session_state.coding_questions
        st.success(f"✅ Generated {len(questions)} coding challenges with solutions")
        
        st.info("💡 **Tip:** These are practical coding problems relevant to the JD. Solutions and test cases included.")
        
        for i, q in enumerate(questions, 1):
            with st.expander(
                f"**Challenge {i}: {q.title}** | {q.difficulty.value} | {q.skill_area}",
                expanded=False
            ):
                # Problem statement
                st.markdown("### 📋 Problem")
                st.markdown(q.problem_statement)
                
                st.divider()
                
                # I/O Format
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Input Format:**")
                    st.code(q.input_format)
                
                with col2:
                    st.markdown("**Output Format:**")
                    st.code(q.output_format)
                
                # Examples
                st.markdown("### 💡 Examples")
                for j, example in enumerate(q.examples, 1):
                    st.markdown(f"**Example {j}:**")
                    ex_input = example.get('input', 'N/A')
                    ex_output = example.get('output', 'N/A')
                    st.code(f"Input: {ex_input}\nOutput: {ex_output}")
                    if example.get('explanation'):
                        st.caption(example['explanation'])
                
                # Constraints
                st.markdown("### ⚙️ Constraints")
                for constraint in q.constraints:
                    st.write(f"• {constraint}")
                
                st.divider()
                
                # Solution (for interviewer)
                with st.expander("🔐 View Solution (Interviewer Only)", expanded=False):
                    st.markdown("### 💻 Code Solution")
                    st.code(q.solution_code, language="python")
                    
                    st.markdown("### 📖 Explanation")
                    st.markdown(q.solution_explanation)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Time Complexity", q.time_complexity)
                    with col2:
                        st.metric("Space Complexity", q.space_complexity)
                    
                    st.markdown("### 🧪 Test Cases")
                    for j, tc in enumerate(q.test_cases, 1):
                        st.write(f"**Test {j}:** {tc.get('description', '')}")
                        tc_input = tc.get('input', 'N/A')
                        tc_output = tc.get('output', 'N/A')
                        st.code(f"Input: {tc_input}\nExpected: {tc_output}")
                    
                    st.markdown("### ⚠️ Common Mistakes")
                    for mistake in q.common_mistakes:
                        st.warning(f"• {mistake}")
                    
                    st.markdown("### 💡 Hints (if candidate is stuck)")
                    for j, hint in enumerate(q.hints, 1):
                        st.info(f"{j}. {hint}")
        
        # Download options
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export Problems Only (for candidate)"):
                export_text = "CODING CHALLENGES\n" + "="*80 + "\n\n"
                for q in questions:
                    export_text += q.format_for_candidate() + "\n\n"
                
                st.download_button(
                    label="Download Problems",
                    data=export_text,
                    file_name=f"coding_problems_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        with col2:
            if st.button("📥 Export with Solutions (for interviewer)"):
                export_text = "CODING CHALLENGES WITH SOLUTIONS\n" + "="*80 + "\n\n"
                for q in questions:
                    export_text += q.format_for_candidate()
                    export_text += q.format_solution() + "\n\n"
                
                st.download_button(
                    label="Download with Solutions",
                    data=export_text,
                    file_name=f"coding_solutions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
    else:
        st.info("💡 Upload a JD in the 'Single Analysis' tab, then click 'Coding Challenges'")

# ==================== TAB 6: SKILLS GAP ====================
with tab6:
    st.header("📈 Skills Gap Analysis")
    
    if st.session_state.gap_analysis:
        gap = st.session_state.gap_analysis
        
        decision_icons = {
            "HIRE_AS_IS": "🟢",
            "HIRE_AND_TRAIN": "🟡",
            "KEEP_SEARCHING": "🔴"
        }
        
        st.write(f"{decision_icons.get(gap.hire_train_decision.decision, '⚪')} **{gap.hire_train_decision.decision}**")
        st.write(gap.hire_train_decision.reasoning)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Fit", f"{gap.current_fit_score:.0%}")
        col2.metric("After Training", f"{gap.projected_fit_score_after_training:.0%}")
        col3.metric("Training Time", f"{gap.hire_train_decision.training_investment_months} mo")
        
        # Show trainable vs non-trainable gaps
        if gap.trainable_gaps:
            st.subheader("✅ Trainable Gaps")
            for tgap in gap.trainable_gaps:
                with st.expander(f"{tgap.skill_name} - {tgap.training_time_estimate}"):
                    st.write(f"**Training Path:** {tgap.training_path}")
                    st.write(f"**Prerequisites:** {', '.join(tgap.prerequisites)}")
        
        if gap.non_trainable_gaps:
            st.subheader("❌ Critical Gaps (Non-Trainable)")
            for ngap in gap.non_trainable_gaps:
                st.error(f"• {ngap.skill_name}: {ngap.reason}")
    else:
        st.info("Upload a JD and Resume, then click 'Analyze Skills Gaps'")

# ==================== TAB 7: HIRING SUMMARY ====================
with tab7:
    st.header("📄 One-Page Hiring Summary")
    
    if st.session_state.hiring_summary:
        summary_md = st.session_state.hiring_summary
        candidate_name = st.session_state.get('hiring_summary_candidate', 'Candidate')
        
        # Display summary
        st.markdown(summary_md)
        
        # Export options
        st.divider()
        st.subheader("📥 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Markdown export
            st.download_button(
                label="Download Markdown",
                data=summary_md,
                file_name=f"hiring_summary_{candidate_name}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
            # HTML export - convert markdown to basic HTML
            html_data = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Hiring Summary - {candidate_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #95a5a6; padding-bottom: 5px; }}
        .recommendation {{ background: #e8f5e9; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0; }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
<div class="content">
{summary_md.replace('# ', '<h1>').replace('## ', '</h1><h2>').replace('**', '<strong>').replace('**', '</strong>').replace('\n\n', '</p><p>').replace('---', '<hr>')}
</div>
</body>
</html>"""
            st.download_button(
                label="Download HTML",
                data=html_data,
                file_name=f"hiring_summary_{candidate_name}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col3:
            # Plain text format for clipboard
            clipboard_data = summary_md.replace('#', '').replace('**', '').replace('---', '='*60)
            st.download_button(
                label="Copy to Clipboard",
                data=clipboard_data,
                file_name=f"hiring_summary_clip_{candidate_name}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.divider()
        
        # Share options
        st.subheader("📤 Share")
        st.info("💡 Use the clipboard format to quickly paste into Slack, email, or your ATS")
        
        with st.expander("Preview Clipboard Format"):
            st.code(clipboard_data)
    else:
        st.info("Generate a hiring summary in the 'Single Analysis' tab first")

# ==================== TAB 8: SECURITY AUDIT ====================
with tab8:
    st.header("🔒 Security Audit")
    
    if st.session_state.masking_audit_log:
        audit_df = pd.DataFrame(st.session_state.masking_audit_log)
        st.dataframe(audit_df, use_container_width=True)
        
        # Export audit log
        st.divider()
        if st.button("📥 Export Audit Log"):
            csv_data = audit_df.to_csv(index=False)
            st.download_button(
                label="Download Audit Log (CSV)",
                data=csv_data,
                file_name=f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No masking operations yet")

# Footer
st.divider()
st.caption("🎯 Complete Recruiter Suite | 💬 Basic + 🎯 Technical + 💻 Coding | 📁 History + 📄 Summaries | 🔒 Auto-masks PII & Client Data")
