# TEKsystems JobFit Analyzer – Single & Batch (v2.3 BATCH + CAPABILITY-AWARE)
# ---------------------------------------------------------------------------
# Enhancements vs v2.2:
#  1) ✅ Capability-aware priorities: auto-extract Top Skills/Ideal Background items from JD
#  2) ✅ Synonym seeding for capability phrases during matching (wider recall)
#  3) ✅ Priority lock & gaps honored in Single and Batch
#  4) ✅ Defensive evidence handling (no .lower() on lists/dicts)
#  5) ✅ Tiered batch results + exports
#
from __future__ import annotations
import io
import os
import re
import zipfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

import streamlit as st
import pandas as pd
import fitz
import docx
from dotenv import load_dotenv

# === External project modules (as in your repo) ===
from security_masker import SecurityMasker, MaskingResult, create_masking_audit_log
from enhanced_semantic_matcher import (
    EnhancedSemanticSkillMatcher,
    ExperienceDepth,
    ActionVerbIntensity,
)

# ---------------------- JD Context ----------------------
@dataclass
class JDContext:
    excluded_skills: List[str] = field(default_factory=list)
    must_have_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    primary_role_type: Optional[str] = None

class JDContextParser:
    def parse_jd(self, jd_text: str) -> JDContext:
        ctx = JDContext()
        if not jd_text:
            return ctx
        exclusion_patterns = [
            r"not\s+looking\s+for[:\s]+([^\.]+)",
            r"not\s+required[:\s]+([^\.]+)",
            r"do\s+not\s+need[:\s]+([^\.]+)",
            r"don't\s+need[:\s]+([^\.]+)",
            r"avoid[:\s]+([^\.]+)",
            r"not\s+hiring\s+for[:\s]+([^\.]+)",
        ]
        for pattern in exclusion_patterns:
            for match in re.findall(pattern, jd_text, flags=re.I|re.M):
                items = re.split(r",|;|\n| or | and |\(|\)", match)
                cleaned = [i.strip() for i in items if i and len(i.strip())>2]
                ctx.excluded_skills.extend(cleaned)
        role_indicators = {
            'product_manager': ['product manager','product owner','pm role','genai productization'],
            'engineer': ['software engineer','developer','backend','frontend','full stack'],
            'data_scientist': ['data scientist','ml engineer','research scientist'],
            'program_manager': ['program manager','delivery lead','implementation lead'],
        }
        jd_lower = jd_text.lower()
        for role, keys in role_indicators.items():
            if any(k in jd_lower for k in keys):
                ctx.primary_role_type = role; break
        return ctx

    def should_exclude_skill(self, skill_name: str, context: JDContext) -> bool:
        skill_lower = (skill_name or '').lower()
        for excluded in context.excluded_skills:
            ex = excluded.lower()
            if ex in skill_lower or skill_lower in ex:
                return True
        return False

    def is_secondary_skill(self, skill_name: str, context: JDContext) -> bool:
        if context and context.primary_role_type == 'product_manager':
            tech = ['pytorch','tensorflow','keras','cuda','transformers','fine-tuning','model training','deep learning']
            s = (skill_name or '').lower()
            return any(t in s for t in tech)
        return False

# ---------------------- Batch Result Model ----------------------
@dataclass
class BatchCandidateDetail:
    candidate_name: str
    fit_score: float
    validated_skills: List = field(default_factory=list)
    weak_skills: List = field(default_factory=list)
    missing_skills: List = field(default_factory=list)
    top_strengths: List[str] = field(default_factory=list)
    key_gaps: List[str] = field(default_factory=list)
    priority_skills_validated: int = 0
    total_priority_skills: int = 0
    hiring_recommendation: str = ""
    full_report_md: str = ""

# ---------------------- App Initialization ----------------------
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

st.set_page_config(page_title="JobFit Analyzer v2.3 (BATCH + CAPABILITY)", layout="wide", initial_sidebar_state="expanded")

# Session state
if "security_masker" not in st.session_state:
    st.session_state.security_masker = SecurityMasker()
if "semantic_matcher" not in st.session_state:
    st.session_state.semantic_matcher = EnhancedSemanticSkillMatcher()
if "jd_context_parser" not in st.session_state:
    st.session_state.jd_context_parser = JDContextParser()
if "masking_audit_log" not in st.session_state:
    st.session_state.masking_audit_log = []
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "locked_jd" not in st.session_state:
    st.session_state.locked_jd = None
if "locked_jd_text" not in st.session_state:
    st.session_state.locked_jd_text = ""
if "locked_priority_skills" not in st.session_state:
    st.session_state.locked_priority_skills = []
if "jd_context" not in st.session_state:
    st.session_state.jd_context = None
if "current_candidate_name" not in st.session_state:
    st.session_state.current_candidate_name = ""
if "batch_results_detailed" not in st.session_state:
    st.session_state.batch_results_detailed = None
if "hiring_summary" not in st.session_state:
    st.session_state.hiring_summary = None

security_masker = st.session_state.security_masker
semantic_matcher = st.session_state.semantic_matcher
jd_context_parser = st.session_state.jd_context_parser

# ---------------------- Helpers (defensive + capability) ----------------------

def to_text(value) -> str:
    """Coerce any value (str/list/dict/None/other) into a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(to_text(v) for v in value if v is not None)
    if isinstance(value, dict):
        return " ".join(f"{k}: {to_text(v)}" for k, v in value.items())
    return str(value)

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("–","-").replace("—","-").replace("‑","-")
    s = s.replace("&"," and ")
    s = re.sub(r"\s+"," ", s).strip()
    return s

def parse_priority_skills(priority_input: str) -> list:
    """Parse and normalize priority skills (robust)."""
    if not priority_input:
        return []
    skills = []
    for raw_line in priority_input.split("\n"):
        line = normalize_text(raw_line.strip())
        if not line:
            continue
        # Keep the line intact, but allow comma-separated too
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if parts:
            skills.extend(parts)
        else:
            skills.append(line)
    # De-dup while preserving order
    seen = set(); out = []
    for s in skills:
        sl = s.lower()
        if sl not in seen:
            out.append(s); seen.add(sl)
    return out

TOP_SECTIONS = [
    'top skills','key skills','core skills','what you will need',
    'ideal background & skills','ideal background and skills',
    'requirements','must have','must-haves','must haves',
    'key outcomes','responsibilities'
]

def extract_top_skills_from_jd(jd_text: str) -> list:
    """Heuristically extract capability lines from common JD sections."""
    if not jd_text:
        return []
    lines = [l.strip() for l in jd_text.splitlines()]
    indices = []
    for i, l in enumerate(lines):
        low = l.strip().lower()
        if any(h in low for h in TOP_SECTIONS):
            indices.append(i)
    extracted = []
    for idx in indices:
        for j in range(idx+1, min(idx+25, len(lines))):
            line = lines[j].strip()
            if not line:
                break
            if re.match(r'^[•*\-\u2022]|^[A-Za-z0-9].+', line):
                cleaned = re.sub(r'^[•*\-\u2022]\s*','', line).strip()
                cleaned = normalize_text(cleaned)
                left = re.split(r"\s*[-:]\s+", cleaned, maxsplit=1)[0]
                if len(left) >= 3:
                    extracted.append(left)
            else:
                break
    if not extracted:
        m = re.search(r'(top\s+skills)[:\-]\s*(.+)$', jd_text, flags=re.I|re.M)
        if m:
            block = m.group(2)
            for piece in re.split(r'[;\n]|\.(\s+|$)', block):
                piece = normalize_text(piece or '')
                if len(piece) >= 3:
                    left = re.split(r"\s*[-:]\s+", piece, maxsplit=1)[0]
                    extracted.append(left)
    # De-dup & cap
    seen = set(); out = []
    for s in extracted:
        sl = s.lower()
        if sl not in seen:
            out.append(s); seen.add(sl)
    return out[:12]

def seed_priority_aliases(priorities: list) -> list:
    """Add synonyms for capability phrases to improve recall in matching."""
    alias_map = {
        'enterprise change management and transformation leadership': [
            'change management leadership','enterprise transformation',
            'organizational change leadership','change adoption leader'
        ],
        'senior stakeholder management and influence': [
            'executive stakeholder management','senior stakeholder influence',
            'exec sponsorship','c-suite stakeholder engagement'
        ],
        'ai / technology platform adoption expertise': [
            'platform adoption','ai platform enablement','technology adoption',
            'product adoption','usage growth'
        ],
        'enablement program design and communication': [
            'enablement programs','training and communications',
            'workshops roadshows demos','user enablement'
        ],
        'operating in ambiguous and resistant environments': [
            'navigating ambiguity','overcoming resistance','organizational resistance management'
        ],
        # Add a few generics that often appear
        'stakeholder management': ['stakeholder engagement','exec stakeholder management','sponsor alignment'],
        'change management': ['organizational change','adoption and change','prosci change']
    }
    out = list(priorities)
    for p in priorities:
        key = p.lower()
        if key in alias_map:
            out.extend(alias_map[key])
    # De-dup
    seen = set(); dedup = []
    for s in out:
        sl = s.lower()
        if sl not in seen:
            dedup.append(s); seen.add(sl)
    return dedup

def process_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    file_bytes = uploaded_file.read()
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return " ".join([pg.get_text() for pg in doc]).strip()
    if ext == "docx":
        d = docx.Document(io.BytesIO(file_bytes))
        return " ".join([p.text for p in d.paragraphs]).strip()
    if ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore").strip()
    return ""

def apply_masking(text: str, doc_type: str, known_clients: list=None, enable_pii: bool=True, enable_client: bool=True):
    if doc_type == "resume" and enable_pii:
        result = security_masker.mask_resume(text)
        audit = create_masking_audit_log(result, "resume")
        st.session_state.masking_audit_log.append(audit)
        return result.masked_text, result
    elif doc_type == "jd" and enable_client:
        result = security_masker.mask_jd(text, known_client_names=known_clients)
        audit = create_masking_audit_log(result, "jd")
        st.session_state.masking_audit_log.append(audit)
        return result.masked_text, result
    return text, MaskingResult(masked_text=text, mask_count=0)

def capitalize_skill(skill_name: str) -> str:
    special = {
        'aws':'AWS','gcp':'GCP','ai':'AI','ml':'ML','nlp':'NLP','sql':'SQL','nosql':'NoSQL',
        'pytorch':'PyTorch','tensorflow':'TensorFlow','kubernetes':'Kubernetes','docker':'Docker',
        'api':'API','rest':'REST','graphql':'GraphQL','genai':'GenAI','llm':'LLM'
    }
    s = (skill_name or '').strip()
    if s.lower() in special:
        return special[s.lower()]
    return s.title()

# ---------------------- Gap Analysis ----------------------

def identify_comprehensive_gaps(validated_skills: list, missing_skills: list, priority_skills: list, jd_context: JDContext=None) -> dict:
    gaps = { 'missing_priority':[], 'weak_priority':[], 'excluded_present':[], 'total_gap_count':0 }
    if not priority_skills:
        return gaps
    validated_dict = {getattr(s,'skill_name','').lower(): s for s in validated_skills}
    missing_dict   = {getattr(s,'skill_name','').lower(): s for s in missing_skills}

    for priority in priority_skills:
        pl = (priority or '').lower()
        if pl in missing_dict:
            gaps['missing_priority'].append({
                'skill': priority,
                'status':'NOT FOUND',
                'severity':'CRITICAL',
                'impact':'Cannot perform core job functions',
                'reasoning': getattr(missing_dict[pl],'reasoning','No evidence in resume')
            })
        elif pl in validated_dict:
            sk = validated_dict[pl]
            score = getattr(sk,'hands_on_score',0)
            if score < 0.55:
                gaps['weak_priority'].append({
                    'skill': priority,
                    'score': score,
                    'status':'INSUFFICIENT',
                    'severity':'HIGH',
                    'current_level': getattr(getattr(sk,'experience_depth',ExperienceDepth.NOT_FOUND),'value','UNKNOWN'),
                    'required_level': 'PROFICIENT or higher',
                    'gap_percentage': int((0.55 - score)*100)
                })

    if jd_context:
        for sk in validated_skills:
            if jd_context_parser.should_exclude_skill(getattr(sk,'skill_name',''), jd_context):
                gaps['excluded_present'].append({
                    'skill': getattr(sk,'skill_name',''),
                    'score': getattr(sk,'hands_on_score',0),
                    'warning':'JD explicitly excludes this skill',
                    'impact':'May indicate wrong role fit'
                })

    gaps['total_gap_count'] = len(gaps['missing_priority']) + len(gaps['weak_priority'])
    return gaps

# ---------------------- Summary (safe evidence) ----------------------

def generate_comprehensive_hiring_summary(report, priority_skills: list, candidate_name: str, jd_context: JDContext=None) -> str:
    validated_skills = report.validated_skills
    missing_skills   = report.missing_skills
    weak_skills      = report.weak_skills
    overall_fit      = report.overall_relevance_score

    gaps = identify_comprehensive_gaps(validated_skills, missing_skills, priority_skills, jd_context)

    if overall_fit >= 0.75 and gaps['total_gap_count'] == 0:
        recommendation = ("HIRE", "Strong fit. Recommend immediate phone screen")
    elif overall_fit >= 0.70 and gaps['total_gap_count'] <= 2:
        recommendation = ("HIRE WITH TRAINING", "Good foundation. Assess learning aptitude")
    elif overall_fit >= 0.60:
        recommendation = ("CONDITIONAL", "Moderate fit. Consider only with strong training support")
    else:
        recommendation = ("KEEP SEARCHING", "Significant gaps. Continue candidate search")

    title = f"# HIRING SUMMARY: {candidate_name}\n**Overall Fit:** {overall_fit:.0%}\n---\n## 🎯 RECOMMENDATION: {recommendation[0]}\n{recommendation[1]}\n---\n## ✅ TOP STRENGTHS\n"

    sorted_validated = sorted(validated_skills, key=lambda x: getattr(x,'hands_on_score',0), reverse=True)
    md = [title]

    top = 0
    for skill in sorted_validated[:5]:
        top += 1
        sname = capitalize_skill(getattr(skill,'skill_name',''))
        score = getattr(skill,'hands_on_score',0)
        exp   = getattr(getattr(skill,'experience_depth',ExperienceDepth.NOT_FOUND),'value','')
        md.append(f"{top}. **{sname}**\n  {exp.title()} level with {'strong' if score>=0.7 else 'moderate'} hands-on evidence ({score:.0%})")
        ev_text = to_text(getattr(skill,'enhanced_evidence',''))
        if any(k in ev_text.lower() for k in ['reduced','increased','improved','achieved','%','revenue','cost']):
            md[-1] += " with measurable outcomes"
        md.append("")

    md.append("---\n## 📊 PRIORITY SKILLS")
    if priority_skills:
        pset = set(s.lower() for s in priority_skills)
        val_p = [s for s in validated_skills if getattr(s,'skill_name','').lower() in pset]
        if len(val_p) == len(priority_skills):
            md.append(f"✅ **All {len(priority_skills)} priority skills validated**\n")
        else:
            md.append(f"⚠️ **{len(val_p)}/{len(priority_skills)} priority skills validated**\n")
            if val_p:
                md.append("**Validated:**")
                for s in val_p:
                    md.append(f"- {capitalize_skill(getattr(s,'skill_name',''))} ({getattr(s,'hands_on_score',0):.0%})")
    else:
        md.append("No priority skills specified\n")

    md.append("---\n## ⚠️ KEY GAPS")
    if gaps['total_gap_count'] == 0:
        md.append("✅ **No significant gaps in priority skills**\n")
    else:
        if gaps['missing_priority']:
            md.append(f"### 🚫 MISSING PRIORITY SKILLS ({len(gaps['missing_priority'])})")
            for g in gaps['missing_priority']:
                md.append(f"**{g['skill']}**: {g['status']}\n- **Impact:** {g['impact']}\n- **Analysis:** {g['reasoning']}\n")
        if gaps['weak_priority']:
            md.append(f"### 📉 INSUFFICIENT PRIORITY SKILLS ({len(gaps['weak_priority'])})")
            for g in gaps['weak_priority']:
                md.append(f"**{g['skill']}**: only {g['score']:.0%} proficiency\n- **Current Level:** {g['current_level']}\n- **Required Level:** {g['required_level']}\n- **Gap:** needs {g['gap_percentage']}% improvement\n")
    return "\n".join(md)

# ---------------------- UI Components ----------------------

def display_skill_card(skill, is_priority: bool, jd_context: JDContext=None):
    is_excluded = False
    is_secondary = False
    if jd_context:
        is_excluded = jd_context_parser.should_exclude_skill(getattr(skill,'skill_name',''), jd_context)
        is_secondary = jd_context_parser.is_secondary_skill(getattr(skill,'skill_name',''), jd_context)

    score = getattr(skill,'hands_on_score',0)
    if is_excluded: color, level = "⚠️", "Excluded by JD"
    elif score >= 0.85: color, level = "🟢","Excellent"
    elif score >= 0.70: color, level = "🟡","Good"
    elif score >= 0.55: color, level = "🟠","Moderate"
    else: color, level = "🔴","Weak"

    exp_depth = getattr(skill,'experience_depth',ExperienceDepth.NOT_FOUND)
    stars = {
        ExperienceDepth.EXPERT:"⭐⭐⭐", ExperienceDepth.PROFICIENT:"⭐⭐",
        ExperienceDepth.COMPETENT:"⭐",   ExperienceDepth.BASIC:"◐",
        ExperienceDepth.MENTIONED_ONLY:"○",
    }.get(exp_depth, "○")

    priority_badge  = "🎯 PRIORITY" if is_priority else ""
    excluded_badge  = "⛔ EXCLUDED BY JD" if is_excluded else ""
    secondary_badge = "ℹ️ SECONDARY" if is_secondary and not is_excluded else ""
    badge = " ".join(x for x in [priority_badge, secondary_badge, excluded_badge] if x)

    with st.expander(f"{color} **{getattr(skill,'skill_name','')}** {stars} {badge} — {score:.0%} hands-on", expanded=False):
        if is_excluded:
            st.error("⚠️ **JD Context Alert:** JD explicitly says NOT looking for this skill")
        elif is_secondary:
            if jd_context and jd_context.primary_role_type:
                st.info(f"ℹ️ For this {jd_context.primary_role_type.replace('_',' ').title()} role, this is a secondary skill")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{score:.0%}", level)
        c2.metric("Experience", getattr(exp_depth,'value','').title())
        ev_text = to_text(getattr(skill,'enhanced_evidence',''))
        indicators = ['increased','reduced','improved','achieved','%','revenue','cost','time','efficiency']
        has_metrics = any(k in ev_text.lower() for k in indicators)
        c3.metric("Outcomes", "✅ Yes" if has_metrics else "○ None")
        st.markdown("**Evidence:**")
        reasoning_text = to_text(getattr(skill,'reasoning',''))
        if reasoning_text:
            st.info(reasoning_text)
        elif ev_text:
            st.info(ev_text)
        else:
            st.write("Skill mentioned in resume")

# ---------------------- Sidebar ----------------------
st.sidebar.title("⚙️ Settings")
st.sidebar.info("**Version 2.3** — Single + Batch + Capability Aware")

enable_pii_masking   = st.sidebar.checkbox("Mask PII (Name, Email, Phone)", value=True)
enable_client_masking= st.sidebar.checkbox("Mask Client Info", value=True)
if enable_client_masking:
    known_clients_input = st.sidebar.text_area("Known Client Names (one per line)", placeholder="Acme Corp\nContoso", height=100)
    known_clients = [c.strip() for c in known_clients_input.split("\n") if c.strip()]
else:
    known_clients = []

st.sidebar.divider()
# JD Lock
st.sidebar.subheader("🔒 Lock JD for Batch Screening")
if st.session_state.locked_jd:
    st.sidebar.success(f"✅ Locked: {st.session_state.locked_jd}")
    if st.sidebar.button("🔓 Unlock JD"):
        st.session_state.locked_jd = None
        st.session_state.locked_jd_text = ""
        st.session_state.locked_priority_skills = []
        st.session_state.jd_context = None
        st.rerun()
else:
    st.sidebar.info("💡 Lock a JD in the Single Analysis tab to reuse in Batch")

# ---------------------- Tabs ----------------------
tab1, tab2, tab7, tab8 = st.tabs([
    "📋 Single Analysis",
    "📊 Batch Processing",
    "📄 Hiring Summary",
    "🔒 Security Audit",
])

# ---------------------- Single Analysis ----------------------
with tab1:
    st.header("📋 Single Candidate Analysis")

    # JD Input
    col1, col2 = st.columns([3,1])
    with col1:
        st.subheader("📄 Job Description")
    with col2:
        if st.session_state.locked_jd and st.button("🔓 Unlock JD"):
            st.session_state.locked_jd = None
            st.session_state.locked_jd_text = ""
            st.session_state.locked_priority_skills = []
            st.session_state.jd_context = None
            st.rerun()

    priority_prefill = None
    if st.session_state.locked_jd:
        jd_text = st.session_state.locked_jd_text
        st.text_area("Locked JD (read-only)", jd_text, height=150, disabled=True)
    else:
        jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf","docx","txt"], key="jd_single")
        jd_text = process_file(jd_file) if jd_file else ""
        if jd_text and st.button("🔒 Lock this JD for batch screening"):
            st.session_state.locked_jd = jd_file.name if jd_file else "Manual Entry"
            st.session_state.locked_jd_text = jd_text
            st.session_state.jd_context = jd_context_parser.parse_jd(jd_text)
            st.rerun()
        # Auto-extract capability phrases to prefill priorities (only when not locked)
        if jd_text and not st.session_state.locked_jd:
            caps = extract_top_skills_from_jd(jd_text)
            if caps:
                st.info("Auto-detected capabilities from JD:")
                st.write(" • " + "  •  ".join(caps))
                if not st.session_state.get('priority_prefill_done_single'):
                    st.session_state['priority_prefill_done_single'] = True
                    st.session_state['priority_prefill_value_single'] = "\n".join(caps)
            priority_prefill = st.session_state.get('priority_prefill_value_single','')

    # Ensure JD context
    if not st.session_state.jd_context and (st.session_state.locked_jd_text or jd_text):
        st.session_state.jd_context = jd_context_parser.parse_jd(st.session_state.locked_jd_text or jd_text)

    # Priority Skills (with prefill)
    if st.session_state.locked_jd:
        priority_skills_input = "\n".join(st.session_state.locked_priority_skills)
        st.text_area("Locked Priority Skills (read-only)", priority_skills_input, height=100, disabled=True)
    else:
        priority_skills_input = st.text_area(
            "🎯 Priority Skills (Must-Have, one per line)",
            placeholder="Enterprise Change Management & Transformation Leadership\nSenior Stakeholder Management & Influence\nAI / Technology Platform Adoption Expertise",
            value=priority_prefill if priority_prefill is not None else "",
            height=120,
            help="List critical capabilities. One per line. We'll keep the phrase as-is."
        )
        if (jd_text or st.session_state.locked_jd_text) and st.button("🔒 Lock Priority Skills"):
            st.session_state.locked_priority_skills = parse_priority_skills(priority_skills_input)
            st.success(f"Locked {len(st.session_state.locked_priority_skills)} priority skills")

    st.divider()

    # Resume
    st.subheader("📃 Resume")
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf","docx","txt"], key="resume_single")
    resume_text = process_file(resume_file) if resume_file else ""

    st.divider()

    # Actions
    c1,c2,c3 = st.columns(3)
    analyze_clicked = c1.button("🔍 Analyze Match", type="primary", use_container_width=True)
    gen_summary     = c2.button("📄 Generate Hiring Summary", use_container_width=True)
    gen_gap         = c3.button("📈 Analyze Skills Gaps", use_container_width=True)

    if analyze_clicked or gen_summary or gen_gap:
        if not (st.session_state.locked_jd_text or jd_text) or not resume_text:
            st.error("❌ Please upload both JD and Resume")
        else:
            with st.spinner("🔍 Analyzing candidate fit..."):
                effective_jd = st.session_state.locked_jd_text or jd_text
                jd_masked, _ = apply_masking(effective_jd, "jd", known_clients, enable_pii_masking, enable_client_masking)
                resume_masked, _ = apply_masking(resume_text, "resume", None, enable_pii_masking, enable_client_masking)

                base_priority = st.session_state.locked_priority_skills or parse_priority_skills(priority_skills_input)
                analysis_priority = seed_priority_aliases(base_priority)

                report = semantic_matcher.analyze_with_priorities(
                    jd_text=jd_masked,
                    resume_text=resume_masked,
                    priority_skills=analysis_priority
                )
                st.session_state.last_report = report
                if resume_file:
                    st.session_state.current_candidate_name = re.sub(r"\.(pdf|docx|txt)$","", resume_file.name, flags=re.I)

                if gen_summary:
                    st.session_state.hiring_summary = generate_comprehensive_hiring_summary(
                        report,
                        base_priority,
                        st.session_state.current_candidate_name or "Candidate",
                        st.session_state.jd_context
                    )
            st.success("✅ Analysis complete!")

    # Results
    if st.session_state.last_report:
        report = st.session_state.last_report
        st.divider(); st.subheader("📊 Analysis Results")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Overall Fit", f"{report.overall_relevance_score:.0%}")
        m2.metric("Validated Skills", len(report.validated_skills))
        m3.metric("Weak Evidence", len(report.weak_skills))
        m4.metric("Missing Skills", len(report.missing_skills))

        base_priority = st.session_state.locked_priority_skills or parse_priority_skills(priority_skills_input)
        gaps = identify_comprehensive_gaps(report.validated_skills, report.missing_skills, base_priority, st.session_state.jd_context)
        if base_priority:
            if gaps['total_gap_count'] == 0:
                st.success(f"🎯 Priority Skills: All {len(base_priority)} validated ✅")
            else:
                st.warning(f"🎯 Priority Skills: {len(base_priority) - gaps['total_gap_count']}/{len(base_priority)} validated – {gaps['total_gap_count']} gap(s)")

        st.divider(); st.subheader("✅ Validated Skills")
        if report.validated_skills:
            normal, secondary, excluded = [], [], []
            for sk in report.validated_skills:
                if st.session_state.jd_context and jd_context_parser.should_exclude_skill(getattr(sk,'skill_name',''), st.session_state.jd_context):
                    excluded.append(sk)
                elif st.session_state.jd_context and jd_context_parser.is_secondary_skill(getattr(sk,'skill_name',''), st.session_state.jd_context):
                    secondary.append(sk)
                else:
                    normal.append(sk)

            st.caption(f"Showing {len(normal)} validated (non-excluded) skills")
            prio_set = set(s.lower() for s in base_priority)
            normal_sorted = sorted(normal, key=lambda s: getattr(s,'hands_on_score',0), reverse=True)
            normal_prio = [s for s in normal_sorted if getattr(s,'skill_name','').lower() in prio_set]
            normal_rest = [s for s in normal_sorted if getattr(s,'skill_name','').lower() not in prio_set]
            for sk in (normal_prio + normal_rest):
                is_prio = getattr(sk,'skill_name','').lower() in prio_set
                display_skill_card(sk, is_prio, st.session_state.jd_context)

            if secondary:
                with st.expander(f"ℹ️ Secondary/Background Skills ({len(secondary)})"):
                    for sk in secondary:
                        display_skill_card(sk, False, st.session_state.jd_context)
            if excluded:
                with st.expander(f"⚠️ Excluded Skills Present ({len(excluded)}) – JD says 'NOT looking for'"):
                    for sk in excluded:
                        display_skill_card(sk, False, st.session_state.jd_context)
        else:
            st.warning("No validated skills found")

        if gaps['total_gap_count'] > 0:
            st.divider(); st.subheader(f"⚠️ Priority Skill Gaps ({gaps['total_gap_count']})")
            if gaps['missing_priority']:
                st.error(f"**{len(gaps['missing_priority'])} Missing Priority Skills:**")
                for g in gaps['missing_priority']:
                    with st.container():
                        st.markdown(f"### ❌ {g['skill']}")
                        c1,c2 = st.columns([1,2])
                        c1.metric("Status", g['status'])
                        c1.metric("Severity", g['severity'])
                        c2.error(f"**Impact:** {g['impact']}")
                        c2.info(f"**Analysis:** {g['reasoning']}")
                        st.divider()
            if gaps['weak_priority']:
                st.warning(f"**{len(gaps['weak_priority'])} Insufficient Priority Skills:**")
                for g in gaps['weak_priority']:
                    with st.container():
                        st.markdown(f"### ⚠️ {g['skill']}")
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Current Score", f"{g['score']:.0%}")
                        c2.metric("Current Level", g['current_level'])
                        c3.metric("Gap", f"{g['gap_percentage']}%")
                        st.info(f"**Required Level:** {g['required_level']}")
                        st.divider()

# ---------------------- Batch Processing ----------------------
with tab2:
    st.header("📊 Batch Candidate Processing")
    st.info("Upload a JD & multiple resumes (or lock a JD in Single Analysis). We'll auto-detect capability phrases and use synonyms to improve matching while keeping your original labels for counts & gaps.")

    # JD source (locked or upload)
    if st.session_state.locked_jd:
        st.success(f"✅ Using locked JD: {st.session_state.locked_jd}")
        batch_jd_text = st.session_state.locked_jd_text
        batch_priority_skills = st.session_state.locked_priority_skills
        batch_jd_context = st.session_state.jd_context
    else:
        st.warning("💡 Lock a JD in the 'Single Analysis' tab first, or upload here")
        batch_jd_file = st.file_uploader("Upload JD", type=["pdf","docx","txt"], key="batch_jd")
        batch_jd_text = process_file(batch_jd_file) if batch_jd_file else ""
        # Prefill capabilities in batch priority input
        batch_prefill = ''
        if batch_jd_text:
            caps = extract_top_skills_from_jd(batch_jd_text)
            if caps:
                st.info("Auto-detected capabilities from JD:")
                st.write(" • " + "  •  ".join(caps))
                if not st.session_state.get('priority_prefill_done_batch'):
                    st.session_state['priority_prefill_done_batch'] = True
                    st.session_state['priority_prefill_value_batch'] = "\n".join(caps)
            batch_prefill = st.session_state.get('priority_prefill_value_batch','')
        batch_priority_input = st.text_area(
            "Priority Skills (one per line)",
            placeholder="Enterprise Change Management & Transformation Leadership\nSenior Stakeholder Management & Influence",
            value=batch_prefill,
            height=120,
            key="batch_priority"
        )
        batch_priority_skills = parse_priority_skills(batch_priority_input)
        batch_jd_context = jd_context_parser.parse_jd(batch_jd_text) if batch_jd_text else None

    st.divider()

    # Resumes
    st.subheader("📂 Upload Candidate Resumes")
    candidate_files = st.file_uploader("Upload multiple resumes (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True, key="batch_resumes")
    if candidate_files:
        st.info(f"📊 {len(candidate_files)} candidate(s) uploaded")

    # Process button
    if st.button("🚀 Process All Candidates", type="primary"):
        if not batch_jd_text:
            st.error("❌ Please upload or lock a JD first")
        elif not candidate_files:
            st.error("❌ Please upload candidate resumes")
        else:
            with st.spinner(f"🔍 Processing {len(candidate_files)} candidates..."):
                # Mask JD once
                jd_masked, _ = apply_masking(batch_jd_text, "jd", known_clients, enable_pii_masking, enable_client_masking)

                results: List[BatchCandidateDetail] = []
                for cand_file in candidate_files:
                    resume_text = process_file(cand_file)
                    if not resume_text:
                        continue
                    resume_masked, _ = apply_masking(resume_text, "resume", None, enable_pii_masking, enable_client_masking)

                    base_priorities = batch_priority_skills or []
                    analysis_priorities = seed_priority_aliases(base_priorities)

                    report = semantic_matcher.analyze_with_priorities(
                        jd_text=jd_masked,
                        resume_text=resume_masked,
                        priority_skills=analysis_priorities
                    )

                    candidate_name = re.sub(r"\.(pdf|docx|txt)$","", cand_file.name, flags=re.I)
                    gaps = identify_comprehensive_gaps(report.validated_skills, report.missing_skills, base_priorities, batch_jd_context)
                    full_summary = generate_comprehensive_hiring_summary(report, base_priorities, candidate_name, batch_jd_context)

                    fit = report.overall_relevance_score
                    if fit >= 0.75 and gaps['total_gap_count'] == 0:
                        rec = "HIRE"
                    elif fit >= 0.70 and gaps['total_gap_count'] <= 2:
                        rec = "HIRE WITH TRAINING"
                    elif fit >= 0.60:
                        rec = "CONDITIONAL"
                    else:
                        rec = "KEEP SEARCHING"

                    top_strengths = [s.skill_name for s in sorted(report.validated_skills, key=lambda x: getattr(x,'hands_on_score',0), reverse=True)[:5]]
                    key_gaps = [g['skill'] for g in gaps['missing_priority']] + [g['skill'] for g in gaps['weak_priority']]

                    results.append(BatchCandidateDetail(
                        candidate_name=candidate_name,
                        fit_score=fit,
                        validated_skills=report.validated_skills,
                        weak_skills=report.weak_skills,
                        missing_skills=report.missing_skills,
                        top_strengths=top_strengths,
                        key_gaps=key_gaps,
                        priority_skills_validated=(len(base_priorities) - gaps['total_gap_count']) if base_priorities else 0,
                        total_priority_skills=len(base_priorities) if base_priorities else 0,
                        hiring_recommendation=rec,
                        full_report_md=full_summary
                    ))

                results.sort(key=lambda r: r.fit_score, reverse=True)
                st.session_state.batch_results_detailed = results
            st.success(f"✅ Processed {len(st.session_state.batch_results_detailed or [])} candidates")

    # Display results
    if st.session_state.batch_results_detailed:
        results = st.session_state.batch_results_detailed
        st.divider(); st.subheader(f"📊 Results for {len(results)} Candidates")
        avg_fit = sum(r.fit_score for r in results)/len(results) if results else 0
        strong_fits = len([r for r in results if r.fit_score >= 0.75])
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Total Candidates", len(results))
        mc2.metric("Average Fit", f"{avg_fit:.0%}")
        mc3.metric("Strong Fits (75%+)", strong_fits)
        mc4.metric("Top Score", f"{results[0].fit_score:.0%}" if results else "N/A")

        def display_candidate_tier(cands: List[BatchCandidateDetail]):
            for i, cand in enumerate(cands, 1):
                color = ("🟢" if cand.fit_score >= 0.75 else "🟡" if cand.fit_score >= 0.70 else "🟠" if cand.fit_score >= 0.60 else "🔴")
                with st.expander(f"{color} #{i}. {cand.candidate_name} – {cand.fit_score:.0%} Fit", expanded=(i<=2)):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.subheader("📊 Quick Stats")
                        met = st.columns(4)
                        met[0].metric("Fit Score", f"{cand.fit_score:.0%}")
                        met[1].metric("Priority Skills", f"{cand.priority_skills_validated}/{cand.total_priority_skills}")
                        met[2].metric("Total Skills", len(cand.validated_skills))
                        met[3].metric("Recommendation", cand.hiring_recommendation)
                        st.subheader("✅ Top Strengths")
                        for s in cand.top_strengths[:3]:
                            st.success(f"• {s}")
                        if cand.key_gaps:
                            st.subheader("⚠️ Key Gaps")
                            for g in cand.key_gaps[:3]:
                                st.warning(f"• {g}")
                    with col2:
                        st.subheader("🎯 Actions")
                        if st.button("📄 View Full Report", key=f"report_{cand.candidate_name}"):
                            st.session_state.hiring_summary = cand.full_report_md
                            st.session_state.current_candidate_name = cand.candidate_name
                            st.success("✅ Full report loaded in 'Hiring Summary' tab")
                        st.download_button(
                            label="📥 Download Summary",
                            data=cand.full_report_md,
                            file_name=f"hiring_summary_{cand.candidate_name}_{datetime.now().strftime('%Y%m%d')}.md",
                            mime="text/markdown",
                            key=f"dl_{cand.candidate_name}"
                        )
                        html_content = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Hiring Summary - {cand.candidate_name}</title></head><body>{cand.full_report_md}</body></html>"""
                        st.download_button(
                            label="📄 Download HTML",
                            data=html_content,
                            file_name=f"summary_{cand.candidate_name}.html",
                            mime="text/html",
                            key=f"html_{cand.candidate_name}"
                        )

        tier_90_plus = [r for r in results if r.fit_score >= 0.90]
        tier_80_89   = [r for r in results if 0.80 <= r.fit_score < 0.90]
        tier_70_79   = [r for r in results if 0.70 <= r.fit_score < 0.80]
        tier_60_69   = [r for r in results if 0.60 <= r.fit_score < 0.70]
        tier_below_60= [r for r in results if r.fit_score < 0.60]

        if tier_90_plus:
            st.subheader("🏆 EXCELLENT FIT (90%+)")
            st.success(f"**{len(tier_90_plus)} candidate(s)** – Immediate consideration recommended")
            display_candidate_tier(tier_90_plus)
        if tier_80_89:
            st.subheader("🟢 STRONG FIT (80–89%)")
            st.info(f"**{len(tier_80_89)} candidate(s)** – Strong contenders")
            display_candidate_tier(tier_80_89)
        if tier_70_79:
            st.subheader("🟡 GOOD FIT (70–79%)")
            st.warning(f"**{len(tier_70_79)} candidate(s)** – Consider with training")
            display_candidate_tier(tier_70_79)
        if tier_60_69:
            st.subheader("🟠 MODERATE FIT (60–69%)")
            display_candidate_tier(tier_60_69)
        if tier_below_60:
            st.subheader("🔴 WEAK FIT (<60%)")
            with st.expander(f"{len(tier_below_60)} candidate(s) – Click to view"):
                display_candidate_tier(tier_below_60)

        st.divider(); st.subheader("📥 Export Options")
        ex1, ex2 = st.columns(2)
        with ex1:
            if st.button("📦 Download All Summaries (ZIP)"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        zf.writestr(f"{r.candidate_name}_{r.fit_score:.0%}.md", r.full_report_md)
                st.download_button(
                    label="📥 Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"batch_summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip"
                )
        with ex2:
            if st.button("📊 Export as Excel"):
                df = pd.DataFrame([{
                    'Candidate': r.candidate_name,
                    'Fit Score': f"{r.fit_score:.0%}",
                    'Priority Skills': f"{r.priority_skills_validated}/{r.total_priority_skills}",
                    'Top Strengths': ', '.join(r.top_strengths[:3]),
                    'Key Gaps': ', '.join(r.key_gaps[:3]),
                    'Recommendation': r.hiring_recommendation
                } for r in results])
                excel_buffer = io.BytesIO()
                df.to_excel(excel_buffer, index=False, engine='openpyxl')
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ---------------------- Hiring Summary ----------------------
with tab7:
    st.header("📄 Hiring Summary")
    if st.session_state.hiring_summary:
        summary_md = st.session_state.hiring_summary
        candidate_name = st.session_state.get('current_candidate_name','Candidate')
        st.markdown(summary_md)
        st.divider(); c1,c2,c3 = st.columns(3)
        c1.download_button(
            label="Download Markdown",
            data=summary_md,
            file_name=f"hiring_summary_{candidate_name}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )
        html_data = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Hiring Summary - {candidate_name}</title></head><body>{summary_md}</body></html>"""
        c2.download_button("Download HTML", data=html_data, file_name=f"summary_{candidate_name}.html", mime="text/html")
        clip = summary_md.replace('#','').replace('**','')
        c3.download_button("Copy to Clipboard", data=clip, file_name=f"summary_clip_{candidate_name}.txt", mime="text/plain")
    else:
        st.info("Generate a summary in Single Analysis or load one from Batch")

# ---------------------- Security Audit ----------------------
with tab8:
    st.header("🔒 Security Audit")
    if st.session_state.masking_audit_log:
        audit_df = pd.DataFrame(st.session_state.masking_audit_log)
        st.dataframe(audit_df, use_container_width=True)
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

st.divider()
st.caption("🎯 JobFit Analyzer v2.3 — Single + Batch + Capability Aware • Stable evidence • Priority lock • Full gaps • Tiered results")
