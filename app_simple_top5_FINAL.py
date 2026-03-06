"""
Simple JobFit Analyzer - Upload Once, View Multiple Ways  (Cost-Optimised)
==========================================================================

Cost optimisations applied to the Streamlit app layer:

1. MERGED JD CALLS
   The original app made 3 separate LLM calls when a recruiter clicked
   different tabs (JD Summary, Skills, Tech Keywords). Each sent the full
   JD text again. Now a single "Analyse JD" call returns ALL three payloads
   at once and stores them in session state. Subsequent tabs just read from
   session state — zero additional LLM calls.

2. CACHED TECH VALIDATION
   Tab 3 previously re-ran validate_candidate() on every Streamlit rerender.
   Results are now stored in session_state and only re-run when the resume
   or selected keywords actually change.

3. SMALLER MODEL FOR HM SUMMARY
   HM Summary generation switched from llama-3.3-70b-versatile (max_tokens=2500)
   to llama-3.1-8b-instant (max_tokens=2000). The task is structured JSON
   extraction from already-validated data — 8b handles it perfectly.

4. TRUNCATED JD/RESUME IN HM PROMPT
   JD and resume excerpts in the HM prompt reduced from 2 000 chars each to
   1 500 chars each.  The structured validation data already captures the
   key facts; the excerpts are just for narrative context.
"""

import os
import json
import re
import streamlit as st
import fitz          # PyMuPDF
import docx
from dotenv import load_dotenv

from simple_top5_validator import SimpleTop5Validator
from security_masker import SecurityMasker, create_masking_audit_log

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────
_JD_MODEL  = "llama-3.3-70b-versatile"   # kept for the merged JD analysis call
_VAL_MODEL = "llama-3.1-8b-instant"      # used for HM summary (structured JSON)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simple JobFit Analyzer",
    page_icon="🎯",
    layout="wide",
)

# ── Session state initialisation ─────────────────────────────────────────────
if "validator" not in st.session_state:
    api_key = os.getenv("GROQ_API_KEY")
    st.session_state.validator = SimpleTop5Validator(api_key=api_key)
    st.session_state.masker = SecurityMasker()
    st.session_state.masking_audit_log = []

    st.session_state.jd_uploaded = False
    st.session_state.resume_uploaded = False

    st.session_state.jd_text = None
    st.session_state.jd_filename = None
    st.session_state.resume_text = None
    st.session_state.resume_filename = None
    st.session_state.candidate_name = None

    # Results
    st.session_state.tech_keywords = None
    st.session_state.jd_summary = None
    st.session_state.comprehensive_skills = None
    st.session_state.validation_results = None
    st.session_state.selected_tech_keywords = None

    # Cached tech validation (avoid re-running on every rerender)
    st.session_state.tech_validation_results = None
    st.session_state.tech_validation_key = None   # hash(keywords + resume)

    # Interview questions state
    st.session_state.interview_questions = None
    st.session_state.interview_questions_key = None

    # HM report preview state
    st.session_state.hm_report_data = None
    st.session_state.hm_report_bytes = None
    st.session_state.hm_report_safe = None
    st.session_state.hm_report_fit_score = 0
    st.session_state.hm_report_fit_label = ""

    # Template management
    st.session_state.saved_templates = []
    st.session_state.skill_weights = {}
    st.session_state.keyword_weights = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_file):
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "".join(page.get_text() for page in doc)
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""


def extract_text_from_docx(docx_file):
    try:
        doc = docx.Document(docx_file)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""


def extract_text_from_file(file):
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    elif file.type == "text/plain":
        return file.read().decode("utf-8")
    else:
        st.error(f"Unsupported file type: {file.type}")
        return ""


def calculate_weighted_fit_score(validations, weights_dict):
    if not validations:
        return 0
    total_weighted = sum(v.validation_score * weights_dict.get(v.skill_name, 1.0) for v in validations)
    total_weight   = sum(weights_dict.get(v.skill_name, 1.0) for v in validations)
    return total_weighted / total_weight if total_weight else 0


def _groq_client():
    """Return a Groq client (created fresh to avoid stale state issues)."""
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def _clean_json(text: str) -> str:
    """Strip markdown fences from LLM output."""
    if "```json" in text:
        return re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
    if "```" in text:
        return re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)
    return text


# ── MERGED JD ANALYSIS FUNCTION ───────────────────────────────────────────────

def run_merged_jd_analysis(jd_text: str):
    """
    ONE LLM call that returns:
      - role summary + search strings   (was Tab 1 call)
      - top 5 comprehensive skills      (was Tab 2 call)
      - technology keywords list        (was Tab 3 call)

    Saves ~2 full JD transmissions per session.
    """
    client = _groq_client()

    prompt = f"""You are an expert recruiter. Analyse this job description and return a single JSON object.

JOB DESCRIPTION:
{jd_text[:3500]}

Return ONLY valid JSON (no markdown):
{{
  "role_summary": "2-3 sentence overview of the role",
  "role_combination": "RoleA + RoleB (e.g. Product Manager + Data Analyst)",
  "experience_level": "X-Y years",
  "ideal_candidate": "1-sentence description of the ideal hire",
  "key_requirements": ["req1", "req2", "req3", "req4", "req5"],
  "naukri_searches": ["search1", "search2", "search3", "search4", "search5"],
  "linkedin_searches": ["search1", "search2", "search3", "search4", "search5"],
  "top_5_skills": [
    "Demonstrable competency 1 (broad enough to capture transferable experience, 5-15 words)",
    "Demonstrable competency 2 (broad enough to capture transferable experience, 5-15 words)",
    "Demonstrable competency 3 (broad enough to capture transferable experience, 5-15 words)",
    "Demonstrable competency 4 (broad enough to capture transferable experience, 5-15 words)",
    "Demonstrable competency 5 (broad enough to capture transferable experience, 5-15 words)"
  ],
  "tech_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5",
                    "keyword6", "keyword7", "keyword8", "keyword9", "keyword10"]
}}

Rules for top_5_skills — this is the most important field:
- Frame as DEMONSTRABLE COMPETENCIES, not JD jargon or domain-specific buzzwords
- Broad enough to capture transferable experience from adjacent domains
- Describes what the person must be able to SHOW they've done, not just the tool/domain
- Good: "Driving adoption of new platforms or processes at scale across organisations"
- Good: "Stakeholder management and influencing at senior/executive level"
- Good: "Designing enablement, training or workshop programs for teams"
- Bad:  "AI adoption strategy" (too literal — excludes valid change management experience)
- Bad:  "Executive AI sponsorship" (too domain-locked)

Rules for tech_keywords:
- Only technology terms: languages, platforms, frameworks, tools, databases, AI/ML tech
- 10-15 items"""

    response = client.chat.completions.create(
        model=_JD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1200,
    )

    result = _clean_json(response.choices[0].message.content.strip())
    data = json.loads(result)

    # Populate session state
    st.session_state.jd_summary = {
        "role_summary":     data.get("role_summary", ""),
        "role_combination": data.get("role_combination", ""),
        "experience_level": data.get("experience_level", ""),
        "ideal_candidate":  data.get("ideal_candidate", ""),
        "key_requirements": data.get("key_requirements", []),
        "naukri_searches":  data.get("naukri_searches", []),
        "linkedin_searches":data.get("linkedin_searches", []),
    }
    skills = data.get("top_5_skills", [])
    st.session_state.comprehensive_skills = skills[:5] if len(skills) >= 5 else skills

    # Also cache these in the validator so it doesn't re-call LLM
    jd_hash = hash(jd_text[:2000])
    st.session_state.validator._jd_cache[jd_hash] = st.session_state.comprehensive_skills

    st.session_state.tech_keywords = data.get("tech_keywords", [])
    st.session_state.selected_tech_keywords = None
    st.session_state.validation_results = None
    st.session_state.tech_validation_results = None
    st.session_state.tech_validation_key = None


# ── INTERVIEW QUESTION GENERATOR ─────────────────────────────────────────────

def _robust_json_parse(raw: str) -> dict:
    """
    Try multiple strategies to extract valid JSON from LLM output.
    Raises ValueError with a helpful message if all strategies fail.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")

    text = raw.strip()

    # Strategy 1: strip markdown fences (```json ... ``` or ``` ... ```)
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            text = m.group(1).strip()
            break

    # Strategy 2: find the outermost { ... } block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    # Strategy 3: remove JS-style comments (// ...)
    text = re.sub(r"//[^\n]*", "", text)

    # Strategy 4: remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed after cleanup: {e}\n\nCleaned text (first 500 chars):\n{text[:500]}")


def _llm_call(client, prompt: str, max_tokens: int = 2000, label: str = "") -> dict:
    """Make a single LLM call and robustly parse the JSON response."""
    response = client.chat.completions.create(
        model=_JD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    raw = response.choices[0].message.content.strip()
    try:
        return _robust_json_parse(raw)
    except ValueError as e:
        raise ValueError(f"[{label}] {e}")


def _gen_situational(client, jd_text: str, resume_text: str, num: int) -> list:
    prompt = f"""You are an expert technical interviewer. Generate {num} situational/scenario-based technical interview questions for this role.

JOB DESCRIPTION:
{jd_text[:1500]}

RESUME (if available):
{resume_text[:1000] if resume_text else "None provided."}

Return ONLY a valid JSON array (no markdown, no comments):
[
  {{
    "skill_area": "e.g. Python / SQL / AWS",
    "difficulty": "Mid-level / Senior",
    "scenario": "2-3 sentence real-world situation the candidate would face in this role",
    "question": "The exact question to ask the candidate",
    "ideal_points": ["what a strong answer covers - point 1", "point 2", "point 3"],
    "red_flags": ["warning sign 1", "warning sign 2"],
    "follow_ups": ["follow-up question 1", "follow-up question 2"]
  }}
]"""
    data = _llm_call(client, prompt, max_tokens=2000, label="situational")
    # Handle both {"situational": [...]} and direct [...]
    if isinstance(data, list):
        return data
    return data.get("situational", data.get("questions", []))


def _gen_behavioral(client, jd_text: str, resume_text: str, num: int) -> list:
    prompt = f"""You are an expert interviewer. Generate {num} behavioral/competency (STAR) interview questions for this role.

JOB DESCRIPTION:
{jd_text[:1500]}

RESUME (if available):
{resume_text[:1000] if resume_text else "None provided."}

Return ONLY a valid JSON array (no markdown, no comments):
[
  {{
    "competency": "e.g. Stakeholder Management / Conflict Resolution / Ownership",
    "question": "Tell me about a time when...",
    "what_good_looks_like": ["STAR element: strong Situation description", "clear Action taken", "measurable Result"],
    "red_flags": ["vague answer without specifics", "blaming others, no ownership"],
    "follow_ups": ["follow-up probe 1", "follow-up probe 2"]
  }}
]"""
    data = _llm_call(client, prompt, max_tokens=1500, label="behavioral")
    if isinstance(data, list):
        return data
    return data.get("behavioral", data.get("questions", []))


def _gen_one_coding_question(client, jd_text: str, resume_text: str, fmt: str, idx: int) -> dict:
    """Generate a single coding challenge of the specified format."""

    format_instructions = {
        "data_preprocessing": """
FORMAT: Data Preprocessing Challenge
- Provide a CSV dataset with 10-12 rows of realistic, messy data
- Include at least 3 data quality issues: missing values (use empty string or null), duplicate rows, inconsistent casing (e.g. "Python" vs "python" vs "PYTHON"), wrong date formats (mix of DD/MM/YYYY and YYYY-MM-DD), numeric values stored as strings
- Task: candidate writes Python (pandas preferred) to clean, deduplicate, standardise, and produce a clean output
- expected_output: show what the cleaned dataframe/CSV should look like (5-6 rows)
- task_description: numbered steps of what to clean/transform (NOT code — just instructions)
- sample_data: the actual raw CSV as a string with headers and rows""",

        "incomplete_code": """
FORMAT: Complete the Code Challenge
- Provide a Python function skeleton relevant to the JD tech stack (data pipeline, ETL, API call, etc.)
- Include 3-5 clearly marked TODO comments with hints of what goes there
- All imports, function signatures, docstrings, and helper logic should be present
- The code must be logically completable — no missing context
- task_description: the skeleton code itself (Python, properly indented)
- sample_data: any input data/constants needed to test the function
- expected_output: what the function should return/print when correctly implemented""",

        "fix_the_bug": """
FORMAT: Fix the Bug Challenge
- Provide a complete-looking Python or SQL script (20-40 lines)
- Embed exactly 3 bugs: mix of (a) off-by-one or logic error, (b) wrong variable/column name, (c) incorrect condition or operator
- Bugs should look plausible — not trivial typos
- task_description: the buggy code itself
- sample_data: sample input to test against
- expected_output: what the corrected code should produce
- solution_approach: list each bug and its fix""",

        "sql_query": """
FORMAT: SQL Query Challenge
- Create 3 related tables with realistic e-commerce or business data (e.g. Products, Customers, Orders, OrderItems, or similar domain matching the JD)
- Each table: 8-10 rows with real-looking values, proper FK relationships
- task_description: 3 SQL queries to write, each progressively harder:
  Q1: simple SELECT with WHERE/GROUP BY
  Q2: JOIN across 2-3 tables with aggregation  
  Q3: complex query with subquery/CTE/window function
- sample_data: the CREATE TABLE + INSERT statements (or just the table data as text)
- expected_output: what Q2 and Q3 should return (show actual result rows)"""
    }

    instr = format_instructions.get(fmt, format_instructions["data_preprocessing"])

    prompt = f"""You are an expert technical interviewer. Generate ONE coding interview challenge.

JOB DESCRIPTION (for skill context):
{jd_text[:1200]}

{instr}

Return ONLY a valid JSON object (no markdown fences, no comments, no trailing commas):
{{
  "title": "Short descriptive title",
  "skill_area": "Python / SQL / Pandas / etc.",
  "difficulty": "Easy / Medium / Hard",
  "challenge_format": "{fmt}",
  "context": "1-2 sentences: business reason why this task matters",
  "sample_data": "The actual data — CSV rows, SQL table content, or code skeleton. Must be substantial and realistic.",
  "task_description": "What the candidate must do — numbered steps for data_preprocessing/sql_query, or the code itself for incomplete_code/fix_the_bug",
  "expected_output": "The correct result — actual data rows or return value",
  "solution_approach": "Interviewer's walkthrough of the correct solution",
  "what_to_look_for": ["technique/insight 1", "technique/insight 2", "technique/insight 3"],
  "common_mistakes": ["mistake 1", "mistake 2"],
  "hints": ["hint to give after 5 min if stuck", "stronger hint if still stuck"],
  "time_limit_minutes": 20
}}"""

    return _llm_call(client, prompt, max_tokens=2500, label=f"coding_{fmt}_{idx}")


def generate_interview_questions(
    jd_text: str,
    resume_text: str,
    question_types: list,
    num_each: int = 3,
    coding_formats: list = None,
) -> dict:
    """
    Generate all requested interview question types.
    Coding questions use one call PER question to avoid token overflow.
    Returns dict with keys: 'situational', 'coding', 'behavioral'
    """
    if coding_formats is None:
        coding_formats = ["data_preprocessing", "incomplete_code", "fix_the_bug", "sql_query"]

    client  = _groq_client()
    result  = {}
    errors  = []

    if "situational" in question_types:
        try:
            result["situational"] = _gen_situational(client, jd_text, resume_text, num_each)
        except Exception as e:
            errors.append(f"Situational questions failed: {e}")
            result["situational"] = []

    if "behavioral" in question_types:
        try:
            result["behavioral"] = _gen_behavioral(client, jd_text, resume_text, num_each)
        except Exception as e:
            errors.append(f"Behavioral questions failed: {e}")
            result["behavioral"] = []

    if "coding" in question_types:
        coding_qs = []
        # Cycle through selected formats to fill num_each questions
        for i in range(num_each):
            fmt = coding_formats[i % len(coding_formats)]
            try:
                q = _gen_one_coding_question(client, jd_text, resume_text, fmt, i + 1)
                coding_qs.append(q)
            except Exception as e:
                errors.append(f"Coding Q{i+1} ({fmt}) failed: {e}")
        result["coding"] = coding_qs

    if errors:
        result["_errors"] = errors

    return result


def _coding_format_badge(fmt: str) -> str:
    """Return emoji + label for a coding challenge format."""
    return {
        "data_preprocessing": "🧹 Data Preprocessing",
        "incomplete_code":    "🧩 Complete the Code",
        "fix_the_bug":        "🐛 Fix the Bug",
        "sql_query":          "🗄️ SQL Query",
    }.get(fmt, f"💻 {fmt.replace('_', ' ').title()}")


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🎯 Simple JobFit Analyzer")
st.caption("Upload JD and Resume once – View multiple analyses | 🔒 PII Protected")

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings & Templates")

    st.subheader("📋 Template Management")

    if st.session_state.jd_uploaded and (
        st.session_state.comprehensive_skills or st.session_state.tech_keywords
    ):
        with st.expander("💾 Save Current as Template", expanded=False):
            template_name = st.text_input(
                "Template Name", placeholder="e.g., Data Engineer – Senior",
                key="template_name_input",
            )
            template_description = st.text_area(
                "Description (Optional)", height=80, key="template_desc_input"
            )
            if st.button("💾 Save Template", use_container_width=True):
                if template_name:
                    template = {
                        "name": template_name,
                        "description": template_description,
                        "jd_filename": st.session_state.jd_filename,
                        "skills": (st.session_state.comprehensive_skills or []).copy(),
                        "skill_weights": st.session_state.skill_weights.copy(),
                        "keywords": (st.session_state.tech_keywords or []).copy(),
                        "selected_keywords": (
                            st.session_state.selected_tech_keywords.copy()
                            if st.session_state.selected_tech_keywords else None
                        ),
                        "keyword_weights": st.session_state.keyword_weights.copy(),
                    }
                    st.session_state.saved_templates.append(template)
                    st.success(f"✅ Template '{template_name}' saved!")
                    st.balloons()
                else:
                    st.warning("⚠️ Please enter a template name")

    if st.session_state.saved_templates:
        st.divider()
        st.subheader("📂 Saved Templates")
        st.caption(f"{len(st.session_state.saved_templates)} template(s) available")

        for idx, template in enumerate(st.session_state.saved_templates):
            with st.expander(f"📄 {template['name']}", expanded=False):
                if template.get("description"):
                    st.caption(template["description"])
                st.write(f"**Skills**: {len(template['skills'])}")
                st.write(f"**Keywords**: {len(template['keywords'])}")
                st.write(f"**Source JD**: {template.get('jd_filename', 'N/A')}")

                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    if st.button("✅ Load", key=f"load_template_{idx}", use_container_width=True):
                        st.session_state.comprehensive_skills = template["skills"].copy()
                        st.session_state.skill_weights = template["skill_weights"].copy()
                        st.session_state.tech_keywords = template["keywords"].copy()
                        st.session_state.selected_tech_keywords = (
                            template["selected_keywords"].copy()
                            if template["selected_keywords"] else None
                        )
                        st.session_state.keyword_weights = template["keyword_weights"].copy()
                        st.session_state.validation_results = None
                        st.session_state.tech_validation_results = None
                        st.success(f"✅ Loaded: {template['name']}")
                        st.rerun()
                with col_t2:
                    if st.button("🗑️ Delete", key=f"delete_template_{idx}", use_container_width=True):
                        st.session_state.saved_templates.pop(idx)
                        st.rerun()

        st.divider()
        templates_json = json.dumps(st.session_state.saved_templates, indent=2)
        st.download_button(
            "📥 Export All Templates", data=templates_json,
            file_name="jobfit_templates.json", mime="application/json",
            use_container_width=True,
        )
        uploaded_templates = st.file_uploader(
            "📤 Import Templates", type=["json"], key="import_templates"
        )
        if uploaded_templates:
            try:
                imported = json.loads(uploaded_templates.read())
                if isinstance(imported, list):
                    st.session_state.saved_templates.extend(imported)
                    st.success(f"✅ Imported {len(imported)} template(s)")
                    st.rerun()
            except Exception as e:
                st.error(f"Error importing templates: {e}")

    st.divider()
    if st.session_state.jd_uploaded or st.session_state.resume_uploaded:
        st.subheader("📊 Session Stats")
        if st.session_state.jd_uploaded:
            st.metric("JD Status", "✅ Uploaded")
            if st.session_state.comprehensive_skills:
                st.metric("Skills Extracted", len(st.session_state.comprehensive_skills))
            if st.session_state.tech_keywords:
                st.metric("Keywords Extracted", len(st.session_state.tech_keywords))
        if st.session_state.resume_uploaded:
            st.metric("Resume Status", "✅ Uploaded")
            if st.session_state.validation_results:
                st.metric(
                    "Skills Fit Score",
                    f"{st.session_state.validation_results['fit_score']:.0f}/100",
                )

st.divider()

# ── UPLOAD SECTION ────────────────────────────────────────────────────────────
st.header("📤 Upload Documents")

with st.expander("🔒 Security Settings"):
    col_sec1, col_sec2 = st.columns(2)
    with col_sec1:
        enable_pii_masking = st.checkbox(
            "Mask Resume PII (Email, Phone, Address)", value=True,
        )
    with col_sec2:
        enable_jd_masking = st.checkbox(
            "Mask JD Client Info (Company names, Budget)", value=True,
        )

col_upload1, col_upload2 = st.columns(2)

# JD Upload
with col_upload1:
    st.subheader("📄 Job Description")
    jd_file = st.file_uploader(
        "Upload JD", type=["pdf", "docx", "txt"], key="main_jd_upload"
    )

    if jd_file and (
        not st.session_state.jd_uploaded
        or st.session_state.jd_filename != jd_file.name
    ):
        with st.spinner("📖 Reading JD..."):
            jd_text = extract_text_from_file(jd_file)
            if jd_text:
                if enable_jd_masking:
                    mask_result = st.session_state.masker.mask_jd(jd_text, known_client_names=[])
                    jd_text = mask_result.masked_text
                    if mask_result.mask_count > 0:
                        entry = create_masking_audit_log(mask_result, "jd")
                        entry["filename"] = jd_file.name
                        st.session_state.masking_audit_log.append(entry)

                st.session_state.jd_text = jd_text
                st.session_state.jd_filename = jd_file.name
                st.session_state.jd_uploaded = True

                # Reset all derived state when JD changes
                st.session_state.tech_keywords = None
                st.session_state.jd_summary = None
                st.session_state.comprehensive_skills = None
                st.session_state.validation_results = None
                st.session_state.selected_tech_keywords = None
                st.session_state.tech_validation_results = None
                st.session_state.tech_validation_key = None

                st.success(f"✅ JD uploaded: {jd_file.name}")
                st.info("👇 Click 'Analyse JD' below to extract all insights in one go")

    if st.session_state.jd_uploaded:
        st.success(f"✅ **JD Ready**: {st.session_state.jd_filename}")
        status_parts = []
        if st.session_state.tech_keywords:
            status_parts.append(f"🔧 {len(st.session_state.tech_keywords)} keywords")
        if st.session_state.comprehensive_skills:
            status_parts.append(f"🎯 {len(st.session_state.comprehensive_skills)} skills")
        if st.session_state.jd_summary:
            status_parts.append("📋 Summary ready")
        st.caption(" | ".join(status_parts) if status_parts else "👇 Click 'Analyse JD' to start")

# Resume Upload
with col_upload2:
    st.subheader("📄 Resume")
    if st.session_state.jd_uploaded:
        resume_file = st.file_uploader(
            "Upload Resume", type=["pdf", "docx", "txt"], key="main_resume_upload"
        )

        if resume_file and (
            not st.session_state.resume_uploaded
            or st.session_state.resume_filename != resume_file.name
        ):
            with st.spinner("📖 Processing Resume..."):
                resume_text = extract_text_from_file(resume_file)
                if resume_text:
                    first_line = resume_text.split("\n")[0].strip()
                    candidate_name = first_line if len(first_line) < 50 else "Candidate"

                    if enable_pii_masking:
                        mask_result = st.session_state.masker.mask_resume(resume_text)
                        resume_text = mask_result.masked_text
                        if mask_result.mask_count > 0:
                            entry = create_masking_audit_log(mask_result, "resume")
                            entry["filename"] = resume_file.name
                            entry["candidate_name"] = candidate_name
                            st.session_state.masking_audit_log.append(entry)

                    st.session_state.resume_text = resume_text
                    st.session_state.resume_filename = resume_file.name
                    st.session_state.candidate_name = candidate_name
                    st.session_state.resume_uploaded = True

                    # Invalidate cached tech validation when resume changes
                    st.session_state.tech_validation_results = None
                    st.session_state.tech_validation_key = None

                    if st.session_state.comprehensive_skills:
                        with st.spinner(f"🔍 Validating {candidate_name}..."):
                            fit_score, validations = st.session_state.validator.validate_candidate(
                                st.session_state.comprehensive_skills,
                                resume_text,
                                candidate_name,
                            )
                            st.session_state.validation_results = {
                                "fit_score": fit_score,
                                "weighted_fit_score": fit_score,
                                "validations": validations,
                                "skills_used": st.session_state.comprehensive_skills.copy(),
                            }
                    st.success(f"✅ Resume processed: {candidate_name}")

        if st.session_state.resume_uploaded:
            st.success(f"✅ **Resume Ready**: {st.session_state.candidate_name}")
            if st.session_state.validation_results:
                st.metric(
                    "Fit Score",
                    f"{st.session_state.validation_results['fit_score']:.0f}/100",
                )
    else:
        st.info("👈 Upload JD first")

st.divider()

# ── MERGED JD ANALYSIS BUTTON ────────────────────────────────────────────────
if st.session_state.jd_uploaded and not st.session_state.jd_summary:
    st.info(
        "💡 **One click to analyse everything**: Extracts top skills, "
        "tech keywords, and search strings in a single API call."
    )
    if st.button(
        "🚀 Analyse JD (Skills + Keywords + Search Strings)",
        type="primary",
        use_container_width=True,
        key="btn_analyse_jd_merged",
    ):
        with st.spinner("🤖 Analysing JD (one call for everything)…"):
            try:
                run_merged_jd_analysis(st.session_state.jd_text)
                st.success("✅ JD fully analysed! Browse the tabs below.")
                st.rerun()
            except Exception as e:
                st.error(f"Error analysing JD: {e}. Check GROQ_API_KEY.")

st.divider()

# ── RESULTS TABS ──────────────────────────────────────────────────────────────
if st.session_state.jd_uploaded:
    st.header("📊 Analysis Results")

    results_tabs = st.tabs([
        "📋 JD Summary & Search",
        "🎯 Skills Validation",
        "🔧 Technology Keywords",
        "📄 HM Summary Report",
        "❓ Interview Questions",
    ])

    # ── TAB 1: JD SUMMARY & SEARCH STRINGS ───────────────────────────────────
    with results_tabs[0]:
        if not st.session_state.jd_summary:
            st.info("👆 Click 'Analyse JD' above to generate the summary.")
        else:
            summary = st.session_state.jd_summary
            st.markdown(f"### 📄 Detailed Summary: {st.session_state.jd_filename}")
            st.info(summary.get("role_summary", "No summary available"))
            st.divider()

            st.subheader("🔄 Role Combination")
            st.success(f"**{summary.get('role_combination', 'N/A')}**")
            st.caption("💡 Use this when searching for candidates on Naukri/LinkedIn")
            st.divider()

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.subheader("🟢 Naukri Search Strings")
                naukri_text = "\n\n".join(
                    f"{i}. {s}" for i, s in enumerate(summary.get("naukri_searches", []), 1)
                )
                st.text_area("Copy all:", value=naukri_text, height=200, key="naukri_strings")
            with col_s2:
                st.subheader("🔵 LinkedIn Search Strings")
                linkedin_text = "\n\n".join(
                    f"{i}. {s}" for i, s in enumerate(summary.get("linkedin_searches", []), 1)
                )
                st.text_area("Copy all:", value=linkedin_text, height=200, key="linkedin_strings")

            st.divider()
            summary_md = f"""# JD Summary & Search Strings

## {st.session_state.jd_filename}

{summary.get('role_summary', '')}

## Role Combination
**{summary.get('role_combination', '')}**

## Experience Level
{summary.get('experience_level', '')}

## Key Requirements
{chr(10).join(f'- {r}' for r in summary.get('key_requirements', []))}

## Naukri.com Search Strings
{chr(10).join(f'{i}. {s}' for i, s in enumerate(summary.get('naukri_searches', []), 1))}

## LinkedIn Boolean Search Strings
{chr(10).join(f'{i}. {s}' for i, s in enumerate(summary.get('linkedin_searches', []), 1))}
"""
            st.download_button(
                "📥 Download JD Summary & Search Strings",
                data=summary_md,
                file_name=f"jd_summary_{st.session_state.jd_filename.split('.')[0]}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    # ── TAB 2: SKILLS VALIDATION ──────────────────────────────────────────────
    with results_tabs[1]:
        if not st.session_state.comprehensive_skills:
            st.info("👆 Click 'Analyse JD' above to extract skills.")
        else:
            st.markdown(f"### 🎯 Skills Extracted from JD: {st.session_state.jd_filename}")
            st.success(f"✅ {len(st.session_state.comprehensive_skills)} skills identified")

            with st.expander("✏️ Edit Skills (Optional)", expanded=False):
                edited_skills = []
                for i, skill in enumerate(st.session_state.comprehensive_skills):
                    edited = st.text_input(f"Skill {i+1}", value=skill, key=f"edit_skill_{i}")
                    if edited.strip():
                        edited_skills.append(edited.strip())
                if st.button("✅ Apply Edits", use_container_width=True):
                    if edited_skills:
                        st.session_state.comprehensive_skills = edited_skills
                        st.session_state.validation_results = None
                        st.success("✅ Skills updated!")
                        st.rerun()

            with st.expander("⚖️ Set Skill Priorities (Optional)", expanded=False):
                for skill in st.session_state.comprehensive_skills:
                    if skill not in st.session_state.skill_weights:
                        st.session_state.skill_weights[skill] = 1.0
                weights_changed = False
                for skill in st.session_state.comprehensive_skills:
                    col_w1, col_w2 = st.columns([3, 1])
                    with col_w1:
                        label = f"**{skill[:60]}...**" if len(skill) > 60 else f"**{skill}**"
                        st.write(label)
                    with col_w2:
                        cur = st.session_state.skill_weights.get(skill, 1.0)
                        idx = 0 if cur == 2.0 else (1 if cur == 1.0 else 2)
                        opt = st.selectbox(
                            "Priority",
                            ["🔴 Critical", "🟡 Important", "🟢 Nice-to-have"],
                            index=idx,
                            key=f"weight_{hash(skill)}",
                            label_visibility="collapsed",
                        )
                        new_w = 2.0 if "Critical" in opt else (1.0 if "Important" in opt else 0.5)
                        if new_w != st.session_state.skill_weights.get(skill, 1.0):
                            st.session_state.skill_weights[skill] = new_w
                            weights_changed = True
                if weights_changed:
                    st.session_state.validation_results = None
                    st.success("✅ Priorities updated!")

            st.markdown("### 📋 Current Skills")
            for skill in st.session_state.comprehensive_skills:
                w = st.session_state.skill_weights.get(skill, 1.0)
                prefix = "🔴" if w == 2.0 else ("🟢" if w == 0.5 else "•")
                st.write(f"{prefix} {skill}")

            st.divider()

        # Validation results
        if st.session_state.resume_uploaded and st.session_state.comprehensive_skills:
            skills_key = str(st.session_state.comprehensive_skills)
            cached = st.session_state.validation_results
            if (
                not cached
                or cached.get("skills_used") != st.session_state.comprehensive_skills
            ):
                with st.spinner(f"🔍 Validating {st.session_state.candidate_name}…"):
                    fit_score, validations = st.session_state.validator.validate_candidate(
                        st.session_state.comprehensive_skills,
                        st.session_state.resume_text,
                        st.session_state.candidate_name,
                    )
                    weighted = calculate_weighted_fit_score(
                        validations, st.session_state.skill_weights
                    )
                    st.session_state.validation_results = {
                        "fit_score": fit_score,
                        "weighted_fit_score": weighted,
                        "validations": validations,
                        "skills_used": st.session_state.comprehensive_skills.copy(),
                    }

            results = st.session_state.validation_results
            has_custom_weights = any(
                w != 1.0 for w in st.session_state.skill_weights.values()
            )
            display_score = (
                results["weighted_fit_score"] if has_custom_weights else results["fit_score"]
            )

            st.subheader(f"📊 {st.session_state.candidate_name} – Validation Results")
            if display_score >= 75:
                st.success(f"### ✅ STRONG FIT – {display_score:.0f}/100")
            elif display_score >= 60:
                st.warning(f"### ⚠️ CONDITIONAL FIT – {display_score:.0f}/100")
            else:
                st.error(f"### ❌ WEAK FIT – {display_score:.0f}/100")

            if has_custom_weights:
                c1, c2 = st.columns(2)
                c1.metric("Original Fit Score", f"{results['fit_score']:.0f}/100")
                c2.metric(
                    "Weighted Fit Score",
                    f"{results['weighted_fit_score']:.0f}/100",
                    delta=f"{results['weighted_fit_score'] - results['fit_score']:.0f}",
                )

            st.divider()
            st.subheader("🔍 Skill-by-Skill Assessment")
            for i, val in enumerate(results["validations"], 1):
                icon = "✅" if val.has_project_experience else "❌"
                w = st.session_state.skill_weights.get(val.skill_name, 1.0)
                plabel = "🔴 Critical" if w == 2.0 else ("🟢 Nice-to-have" if w == 0.5 else "")
                title = f"{i}. {icon} {val.skill_name} – {val.validation_score:.0f}%"
                if plabel:
                    title += f" | {plabel}"
                with st.expander(title, expanded=False):
                    ca, cb = st.columns([1, 2])
                    with ca:
                        (st.success if val.has_project_experience else st.error)(
                            f"**Project Experience**: {'Yes' if val.has_project_experience else 'No'}"
                        )
                        st.metric("Score", f"{val.validation_score:.0f}%")
                        if w != 1.0:
                            st.metric("Weight", f"{w}x")
                    with cb:
                        st.write(f"**Evidence**: {val.evidence_summary}")
                        st.write(f"**Example**: {val.project_example}")

            st.divider()
            validated_count = sum(1 for v in results["validations"] if v.has_project_experience)
            c1, c2, c3 = st.columns(3)
            c1.metric("Skills with Projects", f"{validated_count}/{len(results['validations'])}")
            c2.metric("Average Score", f"{results['fit_score']:.0f}%")
            c3.metric("Skills Missing", f"{len(results['validations']) - validated_count}")

            st.divider()
        elif st.session_state.jd_uploaded and not st.session_state.resume_uploaded:
            st.info("👆 Upload a resume to see validation results")

    # ── TAB 3: TECHNOLOGY KEYWORDS ────────────────────────────────────────────
    with results_tabs[2]:
        if not st.session_state.tech_keywords:
            st.info("👆 Click 'Analyse JD' above to extract technology keywords.")
        else:
            st.markdown(f"### 🔧 Technology Keywords: {st.session_state.jd_filename}")
            st.success(f"✅ {len(st.session_state.tech_keywords)} tech keywords extracted")

            with st.expander("✏️ Select / Edit Keywords (Optional)", expanded=False):
                selected_keywords = []
                st.markdown("**Select keywords to validate:**")
                col_s1, col_s2, col_s3 = st.columns(3)
                for i, kw in enumerate(st.session_state.tech_keywords):
                    saved = st.session_state.get("selected_tech_keywords")
                    default = (i < 5) if saved is None else (kw in saved)
                    if [col_s1, col_s2, col_s3][i % 3].checkbox(
                        kw, value=default, key=f"tech_kw_select_{i}"
                    ):
                        selected_keywords.append(kw)
                st.divider()
                if selected_keywords:
                    edited_kws = []
                    for i, kw in enumerate(selected_keywords):
                        ek = st.text_input(f"Keyword {i+1}", value=kw, key=f"edit_tech_kw_{i}")
                        if ek.strip():
                            edited_kws.append(ek.strip())
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button("✅ Use Selected", use_container_width=True, type="primary"):
                            st.session_state.selected_tech_keywords = edited_kws
                            st.session_state.tech_validation_results = None
                            st.session_state.tech_validation_key = None
                            st.rerun()
                    with cb2:
                        if st.button("🔄 Reset to All", use_container_width=True):
                            st.session_state.selected_tech_keywords = st.session_state.tech_keywords.copy()
                            st.session_state.tech_validation_results = None
                            st.session_state.tech_validation_key = None
                            st.rerun()

            keywords_to_validate = (
                st.session_state.selected_tech_keywords or st.session_state.tech_keywords
            )

            with st.expander("⚖️ Set Keyword Priorities (Optional)", expanded=False):
                for kw in keywords_to_validate:
                    if kw not in st.session_state.keyword_weights:
                        st.session_state.keyword_weights[kw] = 1.0
                kw_changed = False
                for kw in keywords_to_validate:
                    cw1, cw2 = st.columns([3, 1])
                    with cw1:
                        st.write(f"**{kw}**")
                    with cw2:
                        cur = st.session_state.keyword_weights.get(kw, 1.0)
                        idx = 0 if cur == 2.0 else (1 if cur == 1.0 else 2)
                        opt = st.selectbox(
                            "Priority",
                            ["🔴 Critical", "🟡 Important", "🟢 Nice-to-have"],
                            index=idx,
                            key=f"kw_weight_{hash(kw)}",
                            label_visibility="collapsed",
                        )
                        nw = 2.0 if "Critical" in opt else (1.0 if "Important" in opt else 0.5)
                        if nw != st.session_state.keyword_weights.get(kw, 1.0):
                            st.session_state.keyword_weights[kw] = nw
                            kw_changed = True
                if kw_changed:
                    st.session_state.tech_validation_results = None
                    st.session_state.tech_validation_key = None
                    st.success("✅ Priorities updated!")

            st.markdown(f"### 📋 Keywords for Validation ({len(keywords_to_validate)} selected)")
            for i, kw in enumerate(keywords_to_validate, 1):
                w = st.session_state.keyword_weights.get(kw, 1.0)
                prefix = "🔴" if w == 2.0 else ("🟢" if w == 0.5 else "")
                st.write(f"{prefix} {i}. {kw}")

            st.divider()

            # Tech validation – cached to avoid re-running on every rerender
            if st.session_state.resume_uploaded and st.session_state.resume_text:
                cache_key = hash(
                    str(keywords_to_validate) + (st.session_state.resume_text[:500])
                )
                if (
                    st.session_state.tech_validation_results is None
                    or st.session_state.tech_validation_key != cache_key
                ):
                    with st.spinner("🔍 Validating technology keywords…"):
                        tech_fit, tech_vals = st.session_state.validator.validate_candidate(
                            keywords_to_validate,
                            st.session_state.resume_text,
                            st.session_state.candidate_name,
                        )
                        st.session_state.tech_validation_results = {
                            "fit_score": tech_fit,
                            "validations": tech_vals,
                        }
                        st.session_state.tech_validation_key = cache_key

                tv = st.session_state.tech_validation_results
                tech_fit_score = tv["fit_score"]
                tech_validations = tv["validations"]
                weighted_tech = calculate_weighted_fit_score(
                    tech_validations, st.session_state.keyword_weights
                )
                has_custom = any(
                    st.session_state.keyword_weights.get(kw, 1.0) != 1.0
                    for kw in keywords_to_validate
                )
                display_tech = weighted_tech if has_custom else tech_fit_score

                st.markdown(f"### 📊 Tech Match: {st.session_state.candidate_name}")
                if display_tech >= 75:
                    st.success(f"### ✅ STRONG TECH MATCH – {display_tech:.0f}/100")
                elif display_tech >= 60:
                    st.warning(f"### ⚠️ MODERATE TECH MATCH – {display_tech:.0f}/100")
                else:
                    st.error(f"### ❌ WEAK TECH MATCH – {display_tech:.0f}/100")

                st.divider()
                st.subheader("🔍 Keyword-by-Keyword Match")
                for i, val in enumerate(tech_validations, 1):
                    icon = "✅" if val.has_project_experience else "❌"
                    w = st.session_state.keyword_weights.get(val.skill_name, 1.0)
                    plabel = "🔴 Critical" if w == 2.0 else ("🟢 Nice-to-have" if w == 0.5 else "")
                    title = f"{i}. {icon} {val.skill_name} – {val.validation_score:.0f}%"
                    if plabel:
                        title += f" | {plabel}"
                    with st.expander(title, expanded=False):
                        ca, cb = st.columns([1, 2])
                        with ca:
                            (st.success if val.has_project_experience else st.error)(
                                f"**Found**: {'Yes' if val.has_project_experience else 'No'}"
                            )
                            st.metric("Score", f"{val.validation_score:.0f}%")
                        with cb:
                            st.write(f"**Evidence**: {val.evidence_summary}")
                            st.write(f"**Context**: {val.project_example}")

                st.divider()
                matched = sum(1 for v in tech_validations if v.has_project_experience)
                c1, c2, c3 = st.columns(3)
                c1.metric("Keywords Found", f"{matched}/{len(tech_validations)}")
                c2.metric("Tech Score", f"{tech_fit_score:.0f}%")
                c3.metric("Missing", f"{len(tech_validations) - matched}")


            else:
                st.info("👆 Upload a resume to validate technology keywords")

            # Categorised view
            st.divider()
            st.markdown("### 📂 Categorised View")
            categories = {
                "AI/ML":     ["genai", "rag", "llm", "ml", "ai", "machine learning", "deep learning", "nlp"],
                "Cloud":     ["aws", "azure", "gcp", "cloud", "s3", "ec2"],
                "Languages": ["python", "java", "javascript", "typescript", "go", "rust"],
                "Databases": ["sql", "mongodb", "postgresql", "redis", "mysql"],
                "DevOps":    ["docker", "kubernetes", "jenkins", "ci/cd", "terraform"],
                "Frameworks":["react", "django", "flask", "spring", "node"],
                "Other":     [],
            }
            categorised = {cat: [] for cat in categories}
            for kw in st.session_state.tech_keywords:
                kl = kw.lower()
                placed = False
                for cat, markers in categories.items():
                    if cat != "Other" and any(m in kl for m in markers):
                        categorised[cat].append(kw)
                        placed = True
                        break
                if not placed:
                    categorised["Other"].append(kw)
            for cat, kws in categorised.items():
                if kws:
                    with st.expander(f"📂 {cat} ({len(kws)})", expanded=True):
                        cols = st.columns(3)
                        for idx, kw in enumerate(kws):
                            cols[idx % 3].write(f"• {kw}")



    # ── TAB 4: HM SUMMARY REPORT ──────────────────────────────────────────────
    with results_tabs[3]:
        st.subheader("📄 Hiring Manager Summary Report")
        st.caption("AI-generated summary for the Hiring Manager. Preview in-app, then download if needed.")

        if not st.session_state.resume_uploaded:
            st.info("👆 Upload both JD and Resume to generate the HM Summary Report")
        else:
            # Show candidate + score at a glance
            cp1, cp2 = st.columns([2, 1])
            with cp1:
                st.success(f"✅ {st.session_state.candidate_name}  ·  {st.session_state.jd_filename}")
            with cp2:
                if st.session_state.validation_results:
                    fit_score_disp = (
                        st.session_state.validation_results.get("weighted_fit_score")
                        or st.session_state.validation_results.get("fit_score", 0)
                    )
                    st.metric("Fit Score", f"{fit_score_disp:.0f}/100")

            st.divider()

            if st.button(
                "🚀 Generate HM Summary",
                type="primary",
                use_container_width=True,
                key="btn_hm_report",
            ):
                if not st.session_state.validation_results:
                    st.warning("⚠️ Go to Skills Validation tab and extract skills first.")
                else:
                    with st.spinner("🤖 Generating HM Summary…"):
                        try:
                            import subprocess
                            client = _groq_client()

                            results = st.session_state.validation_results
                            fit_score = (
                                results.get("weighted_fit_score")
                                or results.get("fit_score", 0)
                            )
                            fit_label = (
                                "Strong Fit" if fit_score >= 75
                                else "Conditional Fit" if fit_score >= 60
                                else "Weak Fit"
                            )

                            hm_prompt = f"""You are a senior recruiter writing a concise Hiring Manager Summary.

JOB DESCRIPTION (excerpt):
{st.session_state.jd_text[:1500]}

CANDIDATE: {st.session_state.candidate_name}
RESUME (excerpt):
{st.session_state.resume_text[:1500]}

FIT SCORE: {fit_score:.0f}%
SKILLS VALIDATED:
{chr(10).join(f"- {v.skill_name}: {v.validation_score:.0f}% – {v.evidence_summary}" for v in results['validations'])}

Return ONLY valid JSON:
{{
  "exec_summary": "2-3 sentence summary of overall fit",
  "strengths": [
    {{"title": "Strength title", "evidence": "Specific evidence from resume"}},
    {{"title": "...", "evidence": "..."}}
  ],
  "gaps": [
    {{"title": "Gap title", "detail": "Why this is a gap"}},
    {{"title": "...", "detail": "..."}}
  ],
  "recommendation": "Proceed/Hold/Reject and why",
  "responsibilities": [
    {{"jd": "JD responsibility", "resume": "Resume match or gap"}},
    {{"jd": "...", "resume": "..."}}
  ],
  "skill_match": [
    {{"skill": "Skill", "candidate": "Evidence", "match": "✅ Strong or ⚠️ Partial or ❌ Missing"}},
    {{"skill": "...", "candidate": "...", "match": "..."}}
  ],
  "gap_table": [
    {{"requirement": "JD requirement", "gap": "Gap description"}},
    {{"requirement": "...", "gap": "..."}}
  ]
}}"""

                            response = client.chat.completions.create(
                                model=_VAL_MODEL,   # 8b model – sufficient for structured JSON
                                messages=[{"role": "user", "content": hm_prompt}],
                                temperature=0.2,
                                max_tokens=2000,
                            )

                            result = _clean_json(response.choices[0].message.content.strip())
                            hm_data = json.loads(result)

                            js_data = f"""
const data = {{
  candidateName: {json.dumps(st.session_state.candidate_name)},
  jdTitle: {json.dumps(st.session_state.jd_filename)},
  overallScore: {fit_score:.0f},
  fitLabel: {json.dumps(fit_label)},
  execSummary: {json.dumps(hm_data.get('exec_summary', ''))},
  strengths: {json.dumps(hm_data.get('strengths', []))},
  gaps: {json.dumps(hm_data.get('gaps', []))},
  recommendation: {json.dumps(hm_data.get('recommendation', ''))},
  responsibilities: {json.dumps(hm_data.get('responsibilities', []))},
  skillMatch: {json.dumps(hm_data.get('skill_match', []))},
  gapTable: {json.dumps(hm_data.get('gap_table', []))}
}};
"""
                            app_dir = os.path.dirname(os.path.abspath(__file__))
                            js_template_path = os.path.join(app_dir, "generate_hm_summary.js")

                            if not os.path.exists(js_template_path):
                                st.error(f"❌ Missing: generate_hm_summary.js (expected in {app_dir})")
                                st.stop()

                            js_template = open(js_template_path, encoding="utf-8").read()
                            js_final = js_template.replace(
                                "// ── Sample data (replace with dynamic data from app) ──────────────────────",
                                "// ── AI-Generated data ──────────────────────",
                            )
                            js_final = re.sub(
                                r"const data = \{.*?\};",
                                lambda m: js_data.strip(),
                                js_final,
                                flags=re.DOTALL,
                            )

                            import tempfile, shutil
                            tmp_dir = tempfile.gettempdir()
                            safe = st.session_state.candidate_name.replace(" ", "_").replace("/", "_")
                            # Use forward slashes throughout — Node.js accepts them on Windows
                            # and they never collide with JS escape sequences.
                            tmp_dir_fwd  = tmp_dir.replace("\\", "/")
                            tmp_js   = os.path.join(tmp_dir, f"hm_report_{safe}.js")
                            out_docx = os.path.join(tmp_dir, f"HM_Summary_{safe}.docx")
                            out_docx_fwd = out_docx.replace("\\", "/")

                            # Safely embed the output path using json.dumps so backslashes
                            # and any special chars are correctly escaped for JavaScript.
                            js_final = js_final.replace(
                                "'/home/claude/HM_Summary_Report.docx'",
                                json.dumps(out_docx_fwd),  # produces a properly quoted+escaped JS string
                            )

                            with open(tmp_js, "w", encoding="utf-8") as f:
                                f.write(js_final)

                            node_cmd = shutil.which("node")
                            if not node_cmd:
                                for p in [
                                    r"C:\Program Files\nodejs\node.exe",
                                    r"C:\Program Files (x86)\nodejs\node.exe",
                                    os.path.expanduser(r"~\AppData\Roaming\nvm\current\node.exe"),
                                ]:
                                    if os.path.exists(p):
                                        node_cmd = p
                                        break

                            if not node_cmd:
                                st.error("❌ Node.js not found! Install from https://nodejs.org")
                                st.stop()

                            # Locate npm next to node
                            npm_cmd = shutil.which("npm")
                            if not npm_cmd:
                                node_dir = os.path.dirname(node_cmd)
                                for candidate in ["npm.cmd", "npm"]:
                                    p = os.path.join(node_dir, candidate)
                                    if os.path.exists(p):
                                        npm_cmd = p
                                        break

                            if not npm_cmd:
                                st.error("❌ npm not found! Reinstall Node.js from https://nodejs.org")
                                st.stop()

                            # ── Ensure 'docx' is installed in tmp_dir ────────────────────────
                            node_modules_path = os.path.join(tmp_dir, "node_modules", "docx")
                            if not os.path.exists(node_modules_path):
                                with st.spinner("📦 Installing 'docx' package (first time only)…"):
                                    install_proc = subprocess.run(
                                        [npm_cmd, "install", "docx", "--prefix", tmp_dir],
                                        capture_output=True, text=True, encoding="utf-8",
                                        cwd=tmp_dir,
                                    )
                                    if install_proc.returncode != 0:
                                        st.error(
                                            f"❌ Failed to install 'docx' package.\n\n"
                                            f"Please run manually in your terminal:\n"
                                            f"```\ncd \"{tmp_dir}\"\nnpm install docx\n```\n\n"
                                            f"Error: {install_proc.stderr[:400]}"
                                        )
                                        st.stop()

                            proc = subprocess.run(
                                [node_cmd, tmp_js],
                                capture_output=True, text=True, encoding="utf-8",
                                cwd=tmp_dir,   # cwd=tmp_dir so require('docx') resolves to local node_modules
                            )

                            if proc.returncode == 0 and os.path.exists(out_docx):
                                with open(out_docx, "rb") as f:
                                    docx_bytes = f.read()
                                st.session_state.hm_report_data = hm_data
                                st.session_state.hm_report_bytes = docx_bytes
                                st.session_state.hm_report_safe = safe
                                st.session_state.hm_report_fit_score = fit_score
                                st.session_state.hm_report_fit_label = fit_label
                                st.rerun()
                            else:
                                st.error(f"Report generation failed: {proc.stderr[:300]}")

                        except Exception as e:
                            st.error(f"Error generating report: {e}")
                            import traceback
                            st.code(traceback.format_exc())

            # ── In-app preview (shown after generation) ───────────────────────
            if st.session_state.get("hm_report_data"):
                hd = st.session_state.hm_report_data
                fs = st.session_state.hm_report_fit_score
                fl = st.session_state.hm_report_fit_label

                st.divider()

                # Score banner
                score_color = "green" if fs >= 75 else ("orange" if fs >= 60 else "red")
                st.markdown(
                    f"<h2 style='text-align:center; color:{score_color};'>"
                    f"Overall Match Score: {fs:.0f}% — {fl}</h2>",
                    unsafe_allow_html=True,
                )

                # Executive summary
                st.markdown("---")
                st.markdown("### 📋 Executive Summary")
                st.info(hd.get("exec_summary", ""))

                # Strengths
                st.markdown("---")
                st.markdown("### ✅ Key Strengths")
                for s in hd.get("strengths", []):
                    with st.container():
                        st.markdown(f"**✅ {s.get('title', '')}**")
                        st.markdown(f"> {s.get('evidence', '')}")

                # Gaps
                st.markdown("---")
                st.markdown("### ❌ Key Gaps")
                for g in hd.get("gaps", []):
                    with st.container():
                        st.markdown(f"**❌ {g.get('title', '')}**")
                        st.markdown(f"> {g.get('detail', '')}")

                # Recommendation
                st.markdown("---")
                st.markdown("### 💡 Recommendation")
                st.warning(hd.get("recommendation", ""))

                # JD vs Resume table
                st.markdown("---")
                st.markdown("### 📊 JD vs Resume: Responsibilities")
                resp = hd.get("responsibilities", [])
                if resp:
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(resp).rename(columns={"jd": "Job Description", "resume": "Resume Evidence"}),
                        use_container_width=True,
                        hide_index=True,
                    )

                # Skill match table
                st.markdown("### 🔧 Technical Skill Match")
                skill_match = hd.get("skill_match", [])
                if skill_match:
                    st.dataframe(
                        pd.DataFrame(skill_match).rename(columns={"skill": "Skill", "candidate": "Candidate Evidence", "match": "Match"}),
                        use_container_width=True,
                        hide_index=True,
                    )

                # Gaps table
                st.markdown("### 📋 Gaps Summary")
                gap_tbl = hd.get("gap_table", [])
                if gap_tbl:
                    st.dataframe(
                        pd.DataFrame(gap_tbl).rename(columns={"requirement": "JD Requirement", "gap": "Gap in Resume"}),
                        use_container_width=True,
                        hide_index=True,
                    )

                # Download — available after viewing
                st.markdown("---")
                st.download_button(
                    "📥 Download HM Summary Report (.docx)",
                    data=st.session_state.hm_report_bytes,
                    file_name=f"HM_Summary_{st.session_state.hm_report_safe}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

    # ── TAB 5: INTERVIEW QUESTIONS ────────────────────────────────────────────
    with results_tabs[4]:
        st.subheader("❓ Interview Question Generator")
        st.caption("Generate targeted interview questions from the JD and resume in one click.")

        if not st.session_state.jd_uploaded:
            st.info("👆 Upload a Job Description to generate interview questions.")
        else:
            col_iq1, col_iq2 = st.columns([2, 1])

            with col_iq1:
                st.markdown("**Select question types to generate:**")
                cb_situational = st.checkbox("🎬 Situational / Technical Scenario Questions", value=True,
                    help="Real-world scenario questions testing problem-solving and tech judgment")
                cb_coding = st.checkbox("💻 Coding / Technical Challenge Questions", value=True,
                    help="Hands-on coding problems relevant to the tech stack in the JD")
                cb_behavioral = st.checkbox("🤝 Behavioral / Competency Questions (STAR)", value=True,
                    help="Soft-skill and leadership questions based on JD requirements")

            with col_iq2:
                num_each = st.selectbox("Questions per type", [2, 3, 4, 5], index=1)

            # Coding format options (shown only if coding is checked)
            coding_formats = []
            if cb_coding:
                st.markdown("**💻 Coding challenge formats to include:**")
                ccol1, ccol2 = st.columns(2)
                with ccol1:
                    if st.checkbox("🧹 Data Preprocessing", value=True,
                        help="Messy CSV with nulls, dupes, inconsistent formats — candidate cleans & transforms"):
                        coding_formats.append("data_preprocessing")
                    if st.checkbox("🧩 Complete the Code", value=True,
                        help="Working skeleton with TODO sections — candidate fills in the logic"):
                        coding_formats.append("incomplete_code")
                with ccol2:
                    if st.checkbox("🐛 Fix the Bug", value=True,
                        help="Code with 2-4 intentional logical/syntax errors — candidate finds & fixes"):
                        coding_formats.append("fix_the_bug")
                    if st.checkbox("🗄️ SQL Query Challenge", value=True,
                        help="Related tables with sample data (Products, Customers, Sales) — candidate writes queries"):
                        coding_formats.append("sql_query")

            if not st.session_state.resume_uploaded:
                st.warning("⚠️ No resume uploaded — questions will be based on the JD only.")

            selected_types = []
            if cb_situational:
                selected_types.append("situational")
            if cb_coding:
                selected_types.append("coding")
            if cb_behavioral:
                selected_types.append("behavioral")

            # Cache key: changes when JD, resume, types, formats, or count change
            iq_cache_key = hash(
                str(selected_types)
                + str(num_each)
                + str(coding_formats)
                + (st.session_state.jd_text or "")[:1000]
                + (st.session_state.resume_text or "")[:500]
            )

            generate_btn = st.button(
                "🚀 Generate Interview Questions",
                type="primary",
                use_container_width=True,
                disabled=len(selected_types) == 0,
                key="btn_generate_iq",
            )

            if generate_btn:
                st.session_state.interview_questions = None  # force refresh
                st.session_state.interview_questions_key = None

            if generate_btn or (
                st.session_state.interview_questions is not None
                and st.session_state.interview_questions_key == iq_cache_key
            ):
                if st.session_state.interview_questions is None or generate_btn:
                    if not selected_types:
                        st.warning("⚠️ Select at least one question type.")
                    else:
                        n_calls = (
                            (1 if "situational" in selected_types else 0)
                            + (num_each if "coding" in selected_types else 0)
                            + (1 if "behavioral" in selected_types else 0)
                        )
                        with st.spinner(f"🤖 Generating questions ({n_calls} LLM calls)… this may take 15-30 seconds"):
                            try:
                                iq_data = generate_interview_questions(
                                    jd_text=st.session_state.jd_text,
                                    resume_text=st.session_state.resume_text or "",
                                    question_types=selected_types,
                                    num_each=num_each,
                                    coding_formats=coding_formats,
                                )
                                st.session_state.interview_questions = iq_data
                                st.session_state.interview_questions_key = iq_cache_key
                                # Show any partial errors as warnings (not hard failures)
                                for err in iq_data.get("_errors", []):
                                    st.warning(f"⚠️ {err}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Unexpected error: {e}")
                                import traceback
                                st.code(traceback.format_exc())

            # ── Display questions ─────────────────────────────────────────────
            iq = st.session_state.interview_questions
            if iq and st.session_state.interview_questions_key == iq_cache_key:
                st.divider()
                total_qs = (
                    len(iq.get("situational", []))
                    + len(iq.get("coding", []))
                    + len(iq.get("behavioral", []))
                )
                if total_qs > 0:
                    st.success(f"✅ {total_qs} interview questions generated!")
                else:
                    st.error("❌ No questions were generated. Check the warnings above and try again.")

                # Build markdown for download
                md_lines = [f"# Interview Questions\n",
                            f"**JD**: {st.session_state.jd_filename}"]
                if st.session_state.resume_uploaded:
                    md_lines.append(f"**Candidate**: {st.session_state.candidate_name}")
                md_lines.append("")

                # ── SITUATIONAL ───────────────────────────────────────────────
                situational_qs = iq.get("situational", [])
                if situational_qs:
                    st.markdown("---")
                    st.markdown("## 🎬 Situational / Technical Scenario Questions")
                    md_lines.append("## 🎬 Situational / Technical Scenario Questions\n")

                    for i, q in enumerate(situational_qs, 1):
                        label = f"Q{i}: [{q.get('skill_area','')}/{q.get('difficulty','')}] {q.get('question','')[:80]}..."
                        with st.expander(label, expanded=(i == 1)):
                            col_a, col_b = st.columns([1, 2])
                            with col_a:
                                st.info(f"**Skill**: {q.get('skill_area','')}")
                                st.info(f"**Difficulty**: {q.get('difficulty','')}")
                            with col_b:
                                st.markdown("**📍 Scenario:**")
                                st.write(q.get("scenario", ""))

                            st.markdown("**❓ Question to ask:**")
                            st.success(q.get("question", ""))

                            col_c, col_d = st.columns(2)
                            with col_c:
                                st.markdown("**✅ Ideal answer points:**")
                                for pt in q.get("ideal_points", []):
                                    st.write(f"• {pt}")
                            with col_d:
                                st.markdown("**🚩 Red flags:**")
                                for rf in q.get("red_flags", []):
                                    st.write(f"⚠️ {rf}")

                            st.markdown("**🔍 Follow-up questions:**")
                            for fu in q.get("follow_ups", []):
                                st.write(f"→ {fu}")

                        md_lines.append(f"### Q{i}: {q.get('question','')}")
                        md_lines.append(f"**Skill**: {q.get('skill_area','')} | **Difficulty**: {q.get('difficulty','')}\n")
                        md_lines.append(f"**Scenario**: {q.get('scenario','')}\n")
                        md_lines.append("**Ideal answer points:**")
                        for pt in q.get("ideal_points", []):
                            md_lines.append(f"- {pt}")
                        md_lines.append("\n**Red flags:**")
                        for rf in q.get("red_flags", []):
                            md_lines.append(f"- ⚠️ {rf}")
                        md_lines.append("\n**Follow-ups:**")
                        for fu in q.get("follow_ups", []):
                            md_lines.append(f"- {fu}")
                        md_lines.append("")

                # ── CODING ────────────────────────────────────────────────────
                coding_qs = iq.get("coding", [])
                if coding_qs:
                    st.markdown("---")
                    st.markdown("## 💻 Coding / Technical Challenge Questions")
                    md_lines.append("## 💻 Coding / Technical Challenge Questions\n")

                    for i, q in enumerate(coding_qs, 1):
                        fmt = q.get("challenge_format", "")
                        fmt_badge = _coding_format_badge(fmt)
                        diff = q.get("difficulty", "Medium")
                        diff_color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}.get(diff, "🟡")
                        label = f"Q{i}: {fmt_badge} | {diff_color} {diff} | [{q.get('skill_area','')}] {q.get('title','')}"

                        with st.expander(label, expanded=(i == 1)):
                            # Header row
                            col_h1, col_h2, col_h3 = st.columns(3)
                            col_h1.info(f"**Format**: {fmt_badge}")
                            col_h2.info(f"**Skill**: {q.get('skill_area','')}")
                            col_h3.info(f"⏱️ **Time limit**: {q.get('time_limit_minutes', 20)} min")

                            # Business context
                            st.markdown("**📌 Business Context:**")
                            st.write(q.get("context", ""))

                            st.divider()

                            # Sample data / schema — shown to candidate
                            st.markdown("**📊 Data / Schema (share with candidate):**")
                            st.code(q.get("sample_data", ""), language="sql" if fmt == "sql_query" else "python")

                            st.divider()

                            # Task description
                            if fmt == "incomplete_code":
                                st.markdown("**🧩 Code Skeleton (share with candidate — they fill in TODOs):**")
                                st.code(q.get("task_description", ""), language="python")
                            elif fmt == "fix_the_bug":
                                st.markdown("**🐛 Buggy Code (share with candidate — they find & fix errors):**")
                                st.code(q.get("task_description", ""), language="python")
                            elif fmt == "sql_query":
                                st.markdown("**📝 Queries to Write:**")
                                st.write(q.get("task_description", ""))
                            else:
                                st.markdown("**📝 Task Instructions:**")
                                st.write(q.get("task_description", ""))

                            st.divider()

                            # Interviewer-only section
                            st.markdown("### 🔒 Interviewer Reference (do not share)")

                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown("**✅ Expected Output:**")
                                st.code(q.get("expected_output", ""), language="python")
                            with col_b:
                                st.markdown("**🧠 Solution Approach:**")
                                st.info(q.get("solution_approach", ""))

                            col_c, col_d = st.columns(2)
                            with col_c:
                                st.markdown("**👀 What to look for:**")
                                for pt in q.get("what_to_look_for", []):
                                    st.write(f"✓ {pt}")
                                st.markdown("**⚠️ Common mistakes:**")
                                for m in q.get("common_mistakes", []):
                                    st.write(f"• {m}")
                            with col_d:
                                st.markdown("**💡 Hints (give if stuck):**")
                                for j, h in enumerate(q.get("hints", []), 1):
                                    st.write(f"Hint {j}: {h}")

                        # Markdown export
                        md_lines.append(f"### Q{i}: {q.get('title','')}")
                        md_lines.append(f"**Format**: {fmt_badge} | **Skill**: {q.get('skill_area','')} | **Difficulty**: {diff} | **Time**: {q.get('time_limit_minutes',20)} min\n")
                        md_lines.append(f"**Context**: {q.get('context','')}\n")
                        md_lines.append("**Sample Data / Schema:**")
                        md_lines.append(f"```\n{q.get('sample_data','')}\n```\n")
                        md_lines.append("**Task:**")
                        md_lines.append(f"```\n{q.get('task_description','')}\n```\n")
                        md_lines.append(f"**Expected Output:**\n```\n{q.get('expected_output','')}\n```\n")
                        md_lines.append(f"**Solution Approach**: {q.get('solution_approach','')}\n")
                        md_lines.append("**What to look for:**")
                        for pt in q.get("what_to_look_for", []):
                            md_lines.append(f"- ✓ {pt}")
                        md_lines.append("\n**Common mistakes:**")
                        for m in q.get("common_mistakes", []):
                            md_lines.append(f"- {m}")
                        md_lines.append("\n**Hints:**")
                        for j, h in enumerate(q.get("hints", []), 1):
                            md_lines.append(f"- Hint {j}: {h}")
                        md_lines.append("")

                # ── BEHAVIORAL ────────────────────────────────────────────────
                behavioral_qs = iq.get("behavioral", [])
                if behavioral_qs:
                    st.markdown("---")
                    st.markdown("## 🤝 Behavioral / STAR Competency Questions")
                    md_lines.append("## 🤝 Behavioral / STAR Competency Questions\n")

                    for i, q in enumerate(behavioral_qs, 1):
                        label = f"Q{i}: [{q.get('competency','')}] {q.get('question','')[:80]}..."
                        with st.expander(label, expanded=(i == 1)):
                            st.info(f"**Competency**: {q.get('competency','')}")

                            st.markdown("**❓ Question:**")
                            st.success(q.get("question", ""))

                            col_c, col_d = st.columns(2)
                            with col_c:
                                st.markdown("**✅ What good looks like (STAR):**")
                                for pt in q.get("what_good_looks_like", []):
                                    st.write(f"• {pt}")
                            with col_d:
                                st.markdown("**🚩 Red flags:**")
                                for rf in q.get("red_flags", []):
                                    st.write(f"⚠️ {rf}")

                            st.markdown("**🔍 Follow-up questions:**")
                            for fu in q.get("follow_ups", []):
                                st.write(f"→ {fu}")

                        md_lines.append(f"### Q{i}: {q.get('question','')}")
                        md_lines.append(f"**Competency**: {q.get('competency','')}\n")
                        md_lines.append("**What good looks like:**")
                        for pt in q.get("what_good_looks_like", []):
                            md_lines.append(f"- {pt}")
                        md_lines.append("\n**Red flags:**")
                        for rf in q.get("red_flags", []):
                            md_lines.append(f"- ⚠️ {rf}")
                        md_lines.append("\n**Follow-ups:**")
                        for fu in q.get("follow_ups", []):
                            md_lines.append(f"- {fu}")
                        md_lines.append("")

                # ── Download ──────────────────────────────────────────────────
                st.divider()
                candidate_slug = (
                    st.session_state.candidate_name.replace(" ", "_")
                    if st.session_state.resume_uploaded
                    else "JD_only"
                )
                st.download_button(
                    "📥 Download All Interview Questions (.md)",
                    data="\n".join(md_lines),
                    file_name=f"interview_questions_{candidate_slug}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

else:
    st.info("📤 Upload a Job Description to get started")

# ── Footer / Audit Log ────────────────────────────────────────────────────────
if st.session_state.masking_audit_log:
    st.divider()
    with st.expander("🔒 Security Audit Log"):
        import pandas as pd
        st.dataframe(pd.DataFrame(st.session_state.masking_audit_log), use_container_width=True)

st.caption("🎯 Simple JobFit Analyzer | Upload Once, View Multiple Ways | 🔒 PII Protected")
