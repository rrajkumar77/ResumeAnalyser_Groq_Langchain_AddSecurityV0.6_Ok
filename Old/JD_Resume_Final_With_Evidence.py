"""
TEKsystems JobFit Analyzer - User-Friendly Edition
===================================================

**RECRUITER-FRIENDLY VERSION**

Key Changes from Complex Edition:
1. ✅ Simplified Evidence Display (no technical jargon)
2. ✅ Clear Visual Indicators (🟢🟡🟠🔴 for skill quality)
3. ✅ 3-Click Decision Process
4. ✅ Built-in User Guide
5. ✅ Hiring Recommendations (not just scores)

All Advanced Features Included:
- Security Masking
- Batch Processing
- Interview Questions
- Skills Gap Analysis
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime

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
# Import ContextType from base semantic matcher
try:
    from semantic_skill_matcher import ContextType
except ImportError:
    # Define fallback if not available
    from enum import Enum
    class ContextType(Enum):
        WORK_EXPERIENCE = "WORK_EXPERIENCE"
        EDUCATION = "EDUCATION"
        SKILLS = "SKILLS"
        UNKNOWN = "UNKNOWN"

# Additional recommendation modules
from batch_processor import BatchCandidateProcessor
from improved_question_generator import ImprovedQuestionGenerator
from situational_technical_generator import SituationalTechnicalGenerator
from coding_question_generator import CodingQuestionGenerator
from skills_gap_analyzer import SkillsGapAnalyzer

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
        
        # ✨ NEW: Show actual evidence from resume
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            st.divider()
            st.write("**📄 Evidence from Resume:**")
            
            # Show top 3 pieces of evidence
            for i, evidence in enumerate(skill.enhanced_evidence[:3], 1):
                evidence_text = getattr(evidence, 'evidence_text', '')
                context = getattr(evidence, 'context', ContextType.UNKNOWN)
                score = getattr(evidence, 'hands_on_score', 0)
                action_verb = getattr(evidence, 'action_verb_intensity', None)
                has_metrics_single = getattr(evidence, 'has_metrics', False)
                
                # Determine badge based on evidence quality
                if score >= 0.80:
                    badge = "🟢 Strong"
                elif score >= 0.60:
                    badge = "🟡 Good"
                else:
                    badge = "🟠 Moderate"
                
                with st.expander(f"Evidence {i} - {badge} ({score:.0%})", expanded=(i==1)):
                    # Show the actual text
                    st.markdown(f'> "{evidence_text}"')
                    
                    # Show why this is good evidence
                    st.caption("**Why this validates hands-on experience:**")
                    
                    indicators = []
                    if context == ContextType.WORK_EXPERIENCE:
                        indicators.append("✓ Found in Work Experience (not just Skills section)")
                    
                    if action_verb and action_verb.name in ['LEADERSHIP', 'CORE_DELIVERY']:
                        verb_names = {
                            'LEADERSHIP': 'Leadership verb (Led, Architected, Designed)',
                            'CORE_DELIVERY': 'Action verb (Built, Implemented, Developed)'
                        }
                        indicators.append(f"✓ {verb_names.get(action_verb.name, 'Action verb present')}")
                    
                    if has_metrics_single:
                        indicators.append("✓ Includes measurable outcomes (numbers, percentages)")
                    
                    if hasattr(evidence, 'project_duration_months') and evidence.project_duration_months:
                        indicators.append(f"✓ Project duration: {evidence.project_duration_months} months")
                    
                    for indicator in indicators:
                        st.success(indicator)
                    
                    # Show what would make it stronger
                    if score < 0.80:
                        improvements = []
                        if not has_metrics_single:
                            improvements.append("Could be stronger with measurable outcomes")
                        if not action_verb or action_verb.name == 'PASSIVE':
                            improvements.append("Could be stronger with action verbs (Led, Built, etc.)")
                        
                        if improvements:
                            st.caption("**How to verify in interview:**")
                            for imp in improvements:
                                st.warning(f"⚠️ {imp}")
        else:
            st.caption("*No detailed evidence available*")

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
        st.error("🔴 **WEAK MATCH - Likely Reject**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Below threshold)")
        st.write(f"• Only {priority_validated}/{total_priority} priority skills validated")
        st.write("\n**Recommendation:** Keep searching for better-matched candidates")

# ==================== INITIALIZE COMPONENTS ====================
security_masker = SecurityMasker()
enhanced_matcher = EnhancedSemanticSkillMatcher()
batch_processor = BatchCandidateProcessor(matcher=enhanced_matcher)
question_generator = ImprovedQuestionGenerator()
situational_generator = SituationalTechnicalGenerator()
coding_generator = CodingQuestionGenerator()
gap_analyzer = SkillsGapAnalyzer()

# ==================== SESSION STATE ====================
if "masking_audit_log" not in st.session_state:
    st.session_state.masking_audit_log = []
if "masked_jd" not in st.session_state:
    st.session_state.masked_jd = ""
if "masked_resume" not in st.session_state:
    st.session_state.masked_resume = ""
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = None
if "situational_questions" not in st.session_state:
    st.session_state.situational_questions = None
if "coding_questions" not in st.session_state:
    st.session_state.coding_questions = None
if "gap_analysis" not in st.session_state:
    st.session_state.gap_analysis = None

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("🔒 Security")
    enable_pii_masking = st.checkbox(
        "Auto-mask PII (Email, Phone, SSN)",
        value=True,
        key="enable_pii_masking"
    )
    enable_client_masking = st.checkbox(
        "Auto-mask Client Info",
        value=True,
        key="enable_client_masking"
    )
    
    st.divider()
    
    st.subheader("🎯 Priority Skills")
    st.caption("Enter must-have skills (one per line)")
    priority_skills_input = st.text_area(
        "Priority Skills",
        placeholder="Python\nAWS\nKubernetes",
        height=100,
        key="priority_skills_input",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Quick Guide
    with st.expander("📖 Quick Guide", expanded=False):
        st.write("""
**3-Click Decision:**
1. Check **Overall Fit Score**
   - 85%+ = Interview
   - 70-84% = Phone screen
   - 60-69% = Assessment
   - <60% = Pass

2. Review **Validated Skills**
   - 🟢 = Excellent
   - 🟡 = Good
   - 🟠 = Moderate
   - 🔴 = Weak

3. Read **Hiring Recommendation**
   - Tells you exactly what to do
        """)

# ==================== MAIN UI ====================
st.title("🎯 JobFit Analyzer - User-Friendly Edition")
st.caption("Simple 3-click hiring decisions with AI-powered validation")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📄 Single Analysis",
    "🚀 Batch Processing",
    "💬 Basic Interview Questions",
    "🎯 Technical Scenarios",
    "💻 Coding Challenges",
    "📈 Skills Gap",
    "🔒 Security Audit"
])

# ==================== TAB 1: SINGLE ANALYSIS ====================
with tab1:
    st.header("Single Candidate Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Job Description")
        uploaded_jd = st.file_uploader(
            "Upload JD",
            type=["pdf", "docx", "txt"],
            key="jd_uploader"
        )
        
        if uploaded_jd:
            jd_content = process_file(uploaded_jd)
            masked_jd, jd_mask_result = apply_masking(jd_content, "jd")
            st.session_state.masked_jd = masked_jd
            
            if jd_mask_result.mask_count > 0:
                st.success(f"🔒 Masked {jd_mask_result.mask_count} sensitive items")
    
    with col2:
        st.subheader("Resume")
        uploaded_resume = st.file_uploader(
            "Upload Resume",
            type=["pdf", "docx", "txt"],
            key="resume_uploader"
        )
        
        if uploaded_resume:
            resume_content = process_file(uploaded_resume)
            masked_resume, resume_mask_result = apply_masking(resume_content, "resume")
            st.session_state.masked_resume = masked_resume
            
            if resume_mask_result.mask_count > 0:
                st.success(f"🔒 Masked {resume_mask_result.mask_count} sensitive items")
    
    st.divider()
    
    if st.session_state.masked_jd and st.session_state.masked_resume:
        if st.button("🎯 Analyze Candidate", type="primary", use_container_width=True):
            with st.spinner("Analyzing candidate..."):
                priority_skills = parse_priority_skills(priority_skills_input)
                
                report = enhanced_matcher.analyze_with_priorities(
                    jd_text=st.session_state.masked_jd,
                    resume_text=st.session_state.masked_resume,
                    priority_skills=priority_skills
                )
                
                st.session_state.last_report = report
                
                # Display results immediately
                st.success("✅ Analysis Complete!")
                
                # STEP 1: Overall Score
                st.header("📊 Step 1: Overall Fit Score")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Overall Fit", f"{report.overall_relevance_score:.0%}")
                col2.metric("Validated Skills", len(report.validated_skills))
                col3.metric("Weak Evidence", len(report.weak_skills))
                col4.metric("Missing Skills", len(report.missing_skills))
                
                # STEP 2: Validated Skills
                st.divider()
                st.header("✅ Step 2: Validated Skills")
                
                if report.validated_skills:
                    # Separate priority and non-priority
                    priority_set = set(s.lower().strip() for s in priority_skills)
                    priority_validated = [s for s in report.validated_skills if s.skill_name.lower() in priority_set]
                    other_validated = [s for s in report.validated_skills if s.skill_name.lower() not in priority_set]
                    
                    if priority_validated:
                        st.subheader("🎯 Priority Skills (Must-Have)")
                        for skill in priority_validated:
                            display_skill_card(skill, is_priority=True)
                    
                    if other_validated:
                        st.subheader("📌 Other Validated Skills")
                        for skill in other_validated:
                            display_skill_card(skill, is_priority=False)
                else:
                    st.warning("No skills met validation criteria")
                
                # STEP 3: Hiring Recommendation
                st.divider()
                display_hiring_recommendation(
                    report.overall_relevance_score,
                    report.validated_skills,
                    priority_skills_input,
                    report.missing_skills
                )
                
                # Additional Details (Collapsible)
                with st.expander("⚠️ View Weak Evidence Skills", expanded=False):
                    if report.weak_skills:
                        for skill in report.weak_skills:
                            st.write(f"**{skill.skill_name}** — {skill.hands_on_score:.0%}")
                            st.caption(skill.reasoning)
                            st.divider()
                    else:
                        st.success("No weak evidence skills!")
                
                with st.expander("⊘ View Ignored Skills (Skills Section Only)", expanded=False):
                    if report.ignored_skills:
                        skill_names = [s.skill_name for s in report.ignored_skills]
                        st.warning(f"These {len(skill_names)} skills appear only in Skills section with no project evidence:")
                        st.write(", ".join(skill_names))
                    else:
                        st.success("No ignored skills!")
                
                with st.expander("❌ View Missing Skills", expanded=False):
                    if report.missing_skills:
                        priority_set = set(s.lower().strip() for s in priority_skills)
                        missing_priority = [s for s in report.missing_skills if s.skill_name.lower() in priority_set]
                        missing_other = [s for s in report.missing_skills if s.skill_name.lower() not in priority_set]
                        
                        if missing_priority:
                            st.error("🚨 Missing Priority Skills:")
                            for s in missing_priority:
                                st.write(f"• {s.skill_name}")
                        
                        if missing_other:
                            st.write("\n⚠️ Missing Nice-to-Have Skills:")
                            for s in missing_other:
                                st.write(f"• {s.skill_name}")
                    else:
                        st.success("No missing skills!")
        
        # Additional Actions
        st.divider()
        st.subheader("🎤 Generate Interview Questions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💬 Basic Questions", use_container_width=True):
                with st.spinner("Generating evidence-based questions..."):
                    priority_skills = parse_priority_skills(priority_skills_input)
                    questions = question_generator.generate_questions(
                        jd_text=st.session_state.masked_jd,
                        resume_text=st.session_state.masked_resume,
                        priority_skills=priority_skills
                    )
                    st.session_state.interview_questions = questions
                    st.success(f"✅ {len(questions)} questions ready!")
                    st.info("👉 View in 'Basic Interview Questions' tab")
        
        with col2:
            if st.button("🎯 Technical Scenarios", use_container_width=True):
                with st.spinner("Generating situational questions..."):
                    questions = situational_generator.generate_situational_questions(
                        jd_text=st.session_state.masked_jd,
                        num_questions=8
                    )
                    st.session_state.situational_questions = questions
                    st.success(f"✅ {len(questions)} scenarios ready!")
                    st.info("👉 View in 'Technical Scenarios' tab")
        
        with col3:
            if st.button("💻 Coding Challenges", use_container_width=True):
                with st.spinner("Generating coding questions..."):
                    questions = coding_generator.generate_coding_questions(
                        jd_text=st.session_state.masked_jd,
                        num_questions=5
                    )
                    st.session_state.coding_questions = questions
                    st.success(f"✅ {len(questions)} challenges ready!")
                    st.info("👉 View in 'Coding Challenges' tab")
        
        st.divider()
        if st.button("📈 Analyze Skills Gaps", use_container_width=True):
            with st.spinner("Analyzing gaps..."):
                priority_skills = parse_priority_skills(priority_skills_input)
                gap_report = gap_analyzer.analyze(
                    jd_text=st.session_state.masked_jd,
                    resume_text=st.session_state.masked_resume,
                    priority_skills=priority_skills
                )
                st.session_state.gap_analysis = gap_report
                st.success(f"✅ {gap_report.hire_train_decision.decision}")
                st.info("👉 View in 'Skills Gap' tab")

# ==================== TAB 2: BATCH PROCESSING ====================
with tab2:
    st.header("🚀 Batch Candidate Processing")
    st.write("Upload 1 JD + ZIP of resumes → Get ranked list")
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_jd = st.file_uploader("Upload Job Description", type=["pdf", "docx", "txt"], key="batch_jd")
    
    with col2:
        batch_zip = st.file_uploader("Upload Resumes (ZIP)", type=["zip"], key="batch_zip")
    
    if batch_jd and batch_zip:
        if st.button("🚀 Process Batch", type="primary"):
            with st.spinner("Processing candidates..."):
                jd_text = process_file(batch_jd)
                masked_jd_batch, _ = apply_masking(jd_text, "jd")
                zip_bytes = batch_zip.read()
                priority_skills = parse_priority_skills(priority_skills_input)
                
                result = batch_processor.process_from_zip(
                    jd_text=masked_jd_batch,
                    zip_file_bytes=zip_bytes,
                    priority_skills=priority_skills
                )
                
                st.session_state.batch_results = result
                st.success(f"✅ Processed {result.processed_successfully} candidates")
    
    if st.session_state.batch_results:
        result = st.session_state.batch_results
        stats = result.get_statistics()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Fit", f"{stats['avg_fit_score']:.0%}")
        col2.metric("Strong Matches (75%+)", stats['strong_matches_75plus'])
        col3.metric("Processing Time", stats['processing_time'])
        
        ranked = result.get_ranked_results(min_fit_score=0.60)
        df = pd.DataFrame([r.to_dict() for r in ranked])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ==================== TAB 3: INTERVIEW QUESTIONS ====================
with tab3:
    st.header("🎤 Evidence-Based Interview Questions")
    
    if st.session_state.interview_questions:
        questions = st.session_state.interview_questions
        st.success(f"✅ Generated {len(questions)} professional interview questions based on candidate's actual resume")
        
        st.info("💡 **Tip:** These questions are designed to verify the candidate's hands-on experience. Print or copy these for your interview.")
        
        for i, q in enumerate(questions, 1):
            with st.expander(
                f"**Q{i}: {q.skill}** | {q.difficulty} | {q.lifecycle_phase.value}",
                expanded=False
            ):
                # Candidate's claim section
                st.markdown("### 📋 Candidate's Claim (from Resume)")
                st.info(f'"{q.context_from_resume}..."')
                
                # Main question
                st.markdown("### ❓ Interview Question")
                st.markdown(q.question)
                
                st.divider()
                
                # Answer guide in tabs
                guide_tab1, guide_tab2, guide_tab3 = st.tabs([
                    "✅ What to Listen For",
                    "🚩 Red Flags", 
                    "🔍 Follow-Ups"
                ])
                
                with guide_tab1:
                    st.markdown("**Key Concepts:**")
                    for concept in q.answer_guide.get('concepts', []):
                        st.write(f"• {concept}")
                    
                    st.markdown("\n**Specific Tools/Technologies:**")
                    for tool in q.answer_guide.get('tools', []):
                        st.write(f"• {tool}")
                    
                    st.markdown("\n**Techniques & Approaches:**")
                    for technique in q.answer_guide.get('techniques', []):
                        st.write(f"• {technique}")
                    
                    st.markdown("\n**Depth Indicators (Signs of Real Hands-On Experience):**")
                    for indicator in q.answer_guide.get('depth_indicators', []):
                        st.success(f"✓ {indicator}")
                
                with guide_tab2:
                    st.markdown("**Watch out for these warning signs:**")
                    for flag in q.answer_guide.get('red_flags', []):
                        st.warning(f"⚠️ {flag}")
                
                with guide_tab3:
                    st.markdown("**Use these to dig deeper:**")
                    for j, follow_up in enumerate(q.follow_up_questions, 1):
                        st.write(f"{j}. {follow_up}")
                
                # Evaluation rubric
                with st.expander("📊 Evaluation Rubric", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**🟢 Strong Answer (Hire)**")
                        st.markdown(q.evaluation_rubric.get('strong', 'Good depth and specifics'))
                    
                    with col2:
                        st.markdown("**🟡 Moderate Answer (Maybe)**")
                        st.markdown(q.evaluation_rubric.get('moderate', 'Some knowledge but lacks depth'))
                    
                    with col3:
                        st.markdown("**🔴 Weak Answer (No Hire)**")
                        st.markdown(q.evaluation_rubric.get('weak', 'Vague or contradicts resume'))
        
        # Download option
        st.divider()
        if st.button("📥 Export Questions for Interview"):
            # Create text export
            export_text = "INTERVIEW QUESTIONS\n" + "="*80 + "\n\n"
            for i, q in enumerate(questions, 1):
                export_text += q.format_for_interviewer() + "\n\n"
            
            st.download_button(
                label="Download as Text File",
                data=export_text,
                file_name=f"interview_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    else:
        st.info("💡 Upload a JD and Resume in the 'Single Analysis' tab, then click 'Generate Interview Questions'")

# ==================== TAB 4: TECHNICAL SCENARIOS ====================
with tab4:
    st.header("🎯 Situational Technical Interview Questions")
    
    if st.session_state.situational_questions:
        questions = st.session_state.situational_questions
        st.success(f"✅ Generated {len(questions)} situational scenarios to assess problem-solving")
        
        st.info("💡 **Tip:** These are 'What would you do if...' questions to assess technical judgment and decision-making.")
        
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
    else:
        st.info("Upload a JD and Resume, then click 'Analyze Skills Gaps'")

# ==================== TAB 7: SECURITY AUDIT ====================
with tab7:
    st.header("🔒 Security Audit")
    
    if st.session_state.masking_audit_log:
        audit_df = pd.DataFrame(st.session_state.masking_audit_log)
        st.dataframe(audit_df, use_container_width=True)
    else:
        st.info("No masking operations yet")

# Footer
st.divider()
st.caption("🎯 Complete Interview Suite | 💬 Basic + 🎯 Technical + 💻 Coding | 🔒 Auto-masks PII & Client Data")
