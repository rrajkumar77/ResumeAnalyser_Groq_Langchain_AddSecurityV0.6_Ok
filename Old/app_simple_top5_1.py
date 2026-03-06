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
    st.session_state.top_5_skills = None
    st.session_state.masker = SecurityMasker()
    st.session_state.masking_audit_log = []
    
    # Store JD analysis results to avoid re-upload
    if 'stored_jd_text' not in st.session_state:
        st.session_state.stored_jd_text = None
    if 'stored_jd_filename' not in st.session_state:
        st.session_state.stored_jd_filename = None
    if 'tech_keywords_result' not in st.session_state:
        st.session_state.tech_keywords_result = None
    if 'jd_summary_result' not in st.session_state:
        st.session_state.jd_summary_result = None

# Title and security banner
st.title("🎯 Simple JobFit Analyzer")
st.caption("Extract top 5 skills from JD and validate against resume | 🔒 PII Protected")

# Security settings banner
st.subheader("🔒 Security Settings")

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
        with st.popover("🔍 Security Log"):
            st.write(f"**Total masked:** {len(st.session_state.masking_audit_log)} operations")
            for log in st.session_state.masking_audit_log[-5:]:
                st.caption(f"• {log.get('type', 'unknown')}: {log.get('count', 0)} items")

# Client names input (for JD masking)
if enable_jd_masking:
    with st.expander("🏢 Known Client Names (Optional)", expanded=False):
        st.caption("Add client/company names to specifically mask from JDs")
        
        known_clients_text = st.text_area(
            "Enter client names (one per line)",
            placeholder="Acme Corporation\nTech Solutions Inc\nPharma Global Ltd",
            height=100,
            help="These names will be masked as [CLIENT_NAME_1], [CLIENT_NAME_2], etc."
        )
        
        known_clients = [c.strip() for c in known_clients_text.split('\n') if c.strip()]
        st.session_state.known_clients = known_clients
        
        if known_clients:
            st.success(f"✅ Will mask {len(known_clients)} client name(s)")
else:
    st.session_state.known_clients = []

st.divider()
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
    
    # LLM Status
    if st.session_state.validator.use_llm:
        st.success("🤖 LLM Mode: ACTIVE")
        st.caption("Using Groq API for intelligent extraction")
    else:
        st.warning("📝 Regex Mode: ACTIVE")
        st.caption("LLM unavailable - using keyword matching")
        st.info("💡 Set GROQ_API_KEY for better accuracy")
    
    st.divider()
    
    # Security Status
    st.subheader("🔒 Security Status")
    
    # Count different types
    resume_masked = sum(log.get('count', 0) for log in st.session_state.masking_audit_log if log.get('document_type') == 'resume')
    jd_masked = sum(log.get('count', 0) for log in st.session_state.masking_audit_log if log.get('document_type') == 'jd')
    
    if resume_masked > 0 or jd_masked > 0:
        st.success("✅ Data Protected")
        if resume_masked > 0:
            st.metric("Resume PII Masked", f"{resume_masked} items", delta="Protected", delta_color="off")
        if jd_masked > 0:
            st.metric("JD Client Info Masked", f"{jd_masked} items", delta="Protected", delta_color="off")
    else:
        st.info("ℹ️ No sensitive data masked yet")
    
    with st.expander("🔍 What We Mask"):
        st.markdown("""
        **From Resumes:**
        - 📧 Email addresses
        - 📱 Phone numbers
        - 🏠 Physical addresses
        - 🔢 SSN/Tax IDs
        - 📅 Date of birth
        
        **From JDs:**
        - 🏢 Client company names
        - 🔐 Project codes
        - 💰 Budget/pricing info
        - 📋 Internal references
        - 🔒 Confidential markers
        """)
    
    st.divider()
    
    # Skill template management - Make it more prominent
    st.subheader("💾 Save/Load Skill Templates")
    
    st.markdown("""
    **Why use templates?**
    - Define skills once, reuse many times
    - Consistent evaluation across candidates
    - Quick validation without re-entering skills
    """)
    
    # Save current skills as template
    if st.session_state.top_5_skills:
        st.success("✅ You have 5 skills ready to save!")
        
        with st.expander("💾 Save Current Skills as Template", expanded=True):
            st.write("**Current Skills:**")
            for i, skill in enumerate(st.session_state.top_5_skills, 1):
                st.write(f"{i}. {skill}")
            
            st.divider()
            
            template_name = st.text_input(
                "Give this template a name:",
                placeholder="e.g., GenAI Product Manager, Data Engineer",
                key="template_name",
                help="Choose a memorable name for this skill set"
            )
            
            if template_name:
                if st.button("💾 Save Template", type="primary", use_container_width=True):
                    if 'skill_templates' not in st.session_state:
                        st.session_state.skill_templates = {}
                    
                    st.session_state.skill_templates[template_name] = st.session_state.top_5_skills.copy()
                    st.success(f"✅ Saved template: **{template_name}**")
                    st.balloons()
            else:
                st.info("👆 Enter a template name above to save")
    else:
        st.info("ℹ️ Define 5 skills first (auto-extract or manual entry) to save as template")
    
    st.divider()
    
    # Load saved templates
    if 'skill_templates' in st.session_state and st.session_state.skill_templates:
        st.subheader(f"📂 Your Saved Templates ({len(st.session_state.skill_templates)})")
        
        for template_name in st.session_state.skill_templates.keys():
            with st.expander(f"📋 {template_name}"):
                # Show skills in this template
                st.write("**Skills in this template:**")
                for i, skill in enumerate(st.session_state.skill_templates[template_name], 1):
                    st.write(f"{i}. {skill}")
                
                st.divider()
                
                col_load, col_delete = st.columns(2)
                
                with col_load:
                    if st.button(f"✅ Load", key=f"load_{template_name}", use_container_width=True):
                        st.session_state.top_5_skills = st.session_state.skill_templates[template_name].copy()
                        st.success(f"✅ Loaded: {template_name}")
                        st.rerun()
                
                with col_delete:
                    if st.button(f"🗑️ Delete", key=f"delete_{template_name}", use_container_width=True):
                        del st.session_state.skill_templates[template_name]
                        st.warning(f"Deleted: {template_name}")
                        st.rerun()
    else:
        st.info("📂 No saved templates yet. Save your first one above!")
    
    st.divider()
    
    # Export/Import templates
    with st.expander("📤 Export/Import Templates"):
        st.write("**Share templates with your team or backup your templates**")
        
        # Export
        if 'skill_templates' in st.session_state and st.session_state.skill_templates:
            import json
            
            templates_json = json.dumps(st.session_state.skill_templates, indent=2)
            
            st.download_button(
                label="📥 Download Templates (JSON)",
                data=templates_json,
                file_name="skill_templates.json",
                mime="application/json",
                use_container_width=True,
                help="Download all your templates to share or backup"
            )
        else:
            st.info("No templates to export yet")
        
        st.divider()
        
        # Import
        uploaded_templates = st.file_uploader(
            "📤 Upload Templates (JSON)",
            type=["json"],
            key="upload_templates",
            help="Import templates from a JSON file"
        )
        
        if uploaded_templates:
            try:
                import json
                templates_data = json.load(uploaded_templates)
                
                if isinstance(templates_data, dict):
                    if 'skill_templates' not in st.session_state:
                        st.session_state.skill_templates = {}
                    
                    # Merge with existing templates
                    new_count = 0
                    for name, skills in templates_data.items():
                        if name not in st.session_state.skill_templates:
                            st.session_state.skill_templates[name] = skills
                            new_count += 1
                    
                    st.success(f"✅ Imported {new_count} new template(s)!")
                    st.rerun()
                else:
                    st.error("Invalid template file format")
            except Exception as e:
                st.error(f"Error importing templates: {e}")
    
    st.divider()
    
    st.markdown("""
    ### How It Works
    
    **Auto-extract Mode:**
    1. Upload JD → AI extracts top 5 skills
    2. Edit skills if needed
    3. Validate resumes
    
    **Manual Entry Mode:**
    1. Type 5 skills directly
    2. Save as template (optional)
    3. Reuse for multiple JDs
    
    ### What You Get
    - **Top 5 critical skills** validation
    - **Project experience** check for each
    - **Fit score** (0-100)
    - **Simple recommendation**
    """)
    
    st.divider()
    
    # Quick examples
    with st.expander("💡 Pre-defined Examples"):
        if st.button("📘 GenAI Product Manager"):
            st.session_state.top_5_skills = [
                "GenAI implementation literacy (prompting, RAG, evaluation)",
                "Product/Program execution (PRDs, stakeholder management)",
                "Regulated domain experience (pharma/healthcare)",
                "Communication and structuring (requirements translation)",
                "Quality definition and adoption (rubrics, training)"
            ]
            st.rerun()
        
        if st.button("📗 Data Engineer"):
            st.session_state.top_5_skills = [
                "SQL query optimization for large-scale data processing",
                "Data Warehousing and Data Lakes design",
                "ETL/ELT pipeline development (Azure/AWS)",
                "Performance tuning for business-critical applications",
                "Cross-functional collaboration and data governance"
            ]
            st.rerun()
        
        if st.button("📙 Software Engineer"):
            st.session_state.top_5_skills = [
                "Backend development (Python/Java, APIs, microservices)",
                "Cloud infrastructure (AWS/Azure, Docker, Kubernetes)",
                "Database design and optimization (SQL, NoSQL)",
                "CI/CD pipelines and DevOps practices",
                "Code quality and testing (unit tests, code reviews)"
            ]
            st.rerun()

# Main content - Add tabs (swapped labels only)
main_tabs = st.tabs(["🎯 Skills Validation", "🔧 Technology Keywords", "📋 JD Summary & Search", "ℹ️ How It Works"])

# ==================== TAB 1: SKILLS VALIDATION (was Technology Keywords) ====================
with main_tabs[0]:
    st.header("🎯 Skills Validation")
    st.caption("Extract skills from JD and validate resumes OR use technology keywords")
    
    # Check if keywords were loaded
    if st.session_state.top_5_skills and 'extracted_tech_keywords' in st.session_state:
        if any(skill in st.session_state.extracted_tech_keywords for skill in st.session_state.top_5_skills):
            st.success(f"✅ Using {len(st.session_state.top_5_skills)} keyword(s) for validation")
    
    col_tech1, col_tech2 = st.columns(2)
    
    # Left column - JD upload for keyword extraction
    with col_tech1:
        st.subheader("Step 1: Upload Job Description")
        
        skills_jd_file = st.file_uploader(  # Changed key to avoid duplicate
            "Upload JD (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="skills_jd_file",  # Changed from tech_jd_file
            help="Upload JD to extract skills or keywords"
        )
        
        if skills_jd_file:
            skills_jd_text = extract_text_from_file(skills_jd_file)
            
            if skills_jd_text:
                # Apply JD masking if enabled
                if enable_jd_masking:
                    jd_masking_result = st.session_state.masker.mask_jd(
                        skills_jd_text, 
                        known_client_names=st.session_state.get('known_clients', [])
                    )
                    skills_jd_text = jd_masking_result.masked_text
                
                with st.spinner("🔍 Extracting technology keywords..."):
                    # Use LLM to extract tech keywords
                    if st.session_state.validator.use_llm:
                        try:
                            prompt = f"""Extract ONLY technology-related keywords from this job description.

JOB DESCRIPTION:
{skills_jd_text[:3000]}

Focus on:
- Programming languages (Python, Java, etc.)
- Cloud platforms (AWS, Azure, GCP)
- Frameworks (React, Django, etc.)
- Tools & Technologies (Docker, Kubernetes, etc.)
- AI/ML technologies (GenAI, RAG, LLM, etc.)
- Databases (SQL, MongoDB, etc.)
- DevOps tools (Jenkins, Git, etc.)

Return ONLY a JSON array of technology keywords (10-20 items):
["keyword1", "keyword2", "keyword3", ...]

Just the array, nothing else:"""

                            from groq import Groq
                            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                            
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.1,
                                max_tokens=500
                            )
                            
                            result = response.choices[0].message.content.strip()
                            
                            # Parse JSON
                            if "```" in result:
                                result = re.search(r'```(?:json)?\s*(.*?)\s*```', result, re.DOTALL).group(1)
                            
                            tech_keywords = json.loads(result)
                            
                            st.success(f"✅ Extracted {len(tech_keywords)} technology keywords!")
                            
                            # Display keywords
                            st.subheader("🔧 Technology Keywords")
                            
                            # Group by category (simple heuristic)
                            categories = {
                                "AI/ML": ["genai", "rag", "llm", "ml", "ai", "machine learning", "deep learning", "nlp", "gpt"],
                                "Cloud": ["aws", "azure", "gcp", "cloud", "s3", "ec2", "lambda"],
                                "Languages": ["python", "java", "javascript", "typescript", "go", "rust", "c++", "c#"],
                                "Databases": ["sql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch"],
                                "DevOps": ["docker", "kubernetes", "k8s", "jenkins", "ci/cd", "terraform", "ansible"],
                                "Frameworks": ["react", "django", "flask", "fastapi", "spring", "node", "express"],
                                "Other": []
                            }
                            
                            categorized = {cat: [] for cat in categories.keys()}
                            
                            for keyword in tech_keywords:
                                keyword_lower = keyword.lower()
                                categorized_flag = False
                                
                                for category, markers in categories.items():
                                    if category != "Other" and any(marker in keyword_lower for marker in markers):
                                        categorized[category].append(keyword)
                                        categorized_flag = True
                                        break
                                
                                if not categorized_flag:
                                    categorized["Other"].append(keyword)
                            
                            # Display by category
                            for category, keywords in categorized.items():
                                if keywords:
                                    with st.expander(f"📂 {category} ({len(keywords)})", expanded=True):
                                        cols = st.columns(3)
                                        for idx, kw in enumerate(keywords):
                                            cols[idx % 3].write(f"• {kw}")
                            
                            # Export keywords
                            st.divider()
                            
                            col_exp1, col_exp2 = st.columns(2)
                            
                            with col_exp1:
                                # As comma-separated list
                                keywords_csv = ", ".join(tech_keywords)
                                st.download_button(
                                    label="📄 Download as Text",
                                    data=keywords_csv,
                                    file_name="tech_keywords.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col_exp2:
                                # As JSON
                                keywords_json = json.dumps(tech_keywords, indent=2)
                                st.download_button(
                                    label="📄 Download as JSON",
                                    data=keywords_json,
                                    file_name="tech_keywords.json",
                                    mime="application/json",
                                    use_container_width=True
                                )
                            
                            st.divider()
                            
                            # Store in session state
                            st.session_state.extracted_tech_keywords = tech_keywords
                            
                            # Quick load options
                            st.subheader("🎯 Load Keywords for Validation")
                            
                            col_load1, col_load2 = st.columns(2)
                            
                            with col_load1:
                                if st.button("📌 Use Top 5", use_container_width=True):
                                    st.session_state.top_5_skills = tech_keywords[:5]
                                    st.success(f"✅ Loaded 5 keywords!")
                                    st.rerun()
                            
                            with col_load2:
                                if st.button("📌 Use All Keywords", use_container_width=True):
                                    st.session_state.top_5_skills = tech_keywords
                                    st.success(f"✅ Loaded {len(tech_keywords)} keywords!")
                                    st.rerun()
                            
                            # Or select specific ones
                            st.divider()
                            
                            selected_keywords = st.multiselect(
                                "Or select specific keywords (1-10)",
                                tech_keywords,
                                max_selections=10,
                                help="Choose which keywords to validate"
                            )
                            
                            if selected_keywords:
                                if st.button("✅ Use Selected", use_container_width=True):
                                    st.session_state.top_5_skills = selected_keywords
                                    st.success(f"✅ Loaded {len(selected_keywords)} keyword(s)!")
                                    st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error extracting keywords: {e}")
                            st.info("Try uploading a different JD or check your API key")
                    
                    else:
                        # Fallback - regex extraction
                        st.warning("⚠️ LLM mode not available. Using simple keyword extraction.")
                        
                        common_tech = [
                            "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
                            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "K8s",
                            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
                            "React", "Django", "Flask", "FastAPI", "Node.js",
                            "GenAI", "RAG", "LLM", "GPT", "Machine Learning", "ML",
                            "CI/CD", "Jenkins", "Git", "Terraform", "Ansible"
                        ]
                        
                        found_tech = [tech for tech in common_tech if tech.lower() in skills_jd_text.lower()]
                        
                        st.success(f"✅ Found {len(found_tech)} technology keywords!")
                        
                        st.subheader("🔧 Technology Keywords")
                        cols = st.columns(3)
                        for idx, tech in enumerate(found_tech):
                            cols[idx % 3].write(f"• {tech}")
                        
                        st.session_state.extracted_tech_keywords = found_tech
                        
                        if st.button("📌 Use These Keywords", use_container_width=True):
                            st.session_state.top_5_skills = found_tech[:10]
                            st.success(f"✅ Loaded {len(st.session_state.top_5_skills)} keywords!")
                            st.rerun()
    
    # Right column - Resume validation
    with col_tech2:
        st.subheader("Step 2: Upload Resume")
        
        if st.session_state.top_5_skills:
            st.info(f"📋 Validating against {len(st.session_state.top_5_skills)} keyword(s)")
            
            # Show keywords being validated
            with st.expander("👁️ Keywords for Validation"):
                for i, skill in enumerate(st.session_state.top_5_skills, 1):
                    st.write(f"{i}. {skill}")
            
            tech_resume_file = st.file_uploader(
                "Upload Resume (PDF/DOCX/TXT)",
                type=["pdf", "docx", "txt"],
                key="tech_resume_file"
            )
            
            if tech_resume_file:
                tech_resume_text = extract_text_from_file(tech_resume_file)
                
                if tech_resume_text:
                    # Extract candidate name before masking
                    first_line = tech_resume_text.split('\n')[0].strip()
                    tech_candidate_name = first_line if len(first_line) < 50 else "Candidate"
                    
                    # Apply PII masking if enabled
                    if enable_pii_masking:
                        with st.spinner("🔒 Masking PII..."):
                            masking_result = st.session_state.masker.mask_resume(tech_resume_text)
                            tech_resume_text = masking_result.masked_text
                            
                            if masking_result.mask_count > 0:
                                audit_entry = create_masking_audit_log(masking_result, "resume")
                                audit_entry['filename'] = tech_resume_file.name
                                audit_entry['candidate_name'] = tech_candidate_name
                                st.session_state.masking_audit_log.append(audit_entry)
                                
                                st.success(f"🔒 Masked {masking_result.mask_count} PII items")
                    
                    with st.spinner(f"🔍 Validating {tech_candidate_name}..."):
                        tech_fit_score, tech_validations = st.session_state.validator.validate_candidate(
                            st.session_state.top_5_skills,
                            tech_resume_text,
                            tech_candidate_name
                        )
                    
                    st.success("✅ Validation Complete")
                    
                    # Display results inline
                    st.divider()
                    st.subheader(f"📊 Results: {tech_candidate_name}")
                    
                    # Fit score
                    if tech_fit_score >= 75:
                        st.success(f"### ✅ STRONG FIT - {tech_fit_score:.0f}/100")
                    elif tech_fit_score >= 60:
                        st.warning(f"### ⚠️ CONDITIONAL FIT - {tech_fit_score:.0f}/100")
                    else:
                        st.error(f"### ❌ WEAK FIT - {tech_fit_score:.0f}/100")
                    
                    st.divider()
                    
                    # Keywords found
                    st.subheader("🔍 Keyword Validation")
                    
                    for i, val in enumerate(tech_validations, 1):
                        icon = "✅" if val.has_project_experience else "❌"
                        
                        with st.expander(f"{i}. {icon} {val.skill_name} - {val.validation_score:.0f}%"):
                            if val.has_project_experience:
                                st.success("**Has Project Experience**: Yes")
                            else:
                                st.error("**Has Project Experience**: No")
                            
                            st.write(f"**Evidence**: {val.evidence_summary}")
                            st.write(f"**Example**: {val.project_example}")
                    
                    # Summary
                    st.divider()
                    validated_count = sum(1 for v in tech_validations if v.has_project_experience)
                    
                    col_s1, col_s2 = st.columns(2)
                    col_s1.metric("Keywords with Projects", f"{validated_count}/{len(st.session_state.top_5_skills)}")
                    col_s2.metric("Average Score", f"{tech_fit_score:.0f}%")
                    
                    # Export
                    st.divider()
                    tech_report_md = st.session_state.validator.generate_simple_report(
                        tech_candidate_name,
                        st.session_state.top_5_skills,
                        tech_fit_score,
                        tech_validations
                    )
                    
                    st.download_button(
                        label="📥 Download Report",
                        data=tech_report_md,
                        file_name=f"tech_validation_{tech_candidate_name.replace(' ', '_')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
        else:
            st.info("👈 Extract keywords from JD first, then upload resume here")

# ==================== TAB 2: SKILLS VALIDATION ====================
with main_tabs[1]:
    st.header("🎯 Technology Keywords")
    
    # Check if skills already extracted from JD upload in Technology Keywords
    if st.session_state.get('comprehensive_skills'):
        st.success(f"✅ Using skills from uploaded JD: {st.session_state.stored_jd_filename}")
        st.caption(f"📋 {len(st.session_state.comprehensive_skills)} skills ready for validation")
        
        # Show the skills
        with st.expander("👁️ Skills for Validation", expanded=False):
            for i, skill in enumerate(st.session_state.comprehensive_skills, 1):
                st.write(f"{i}. {skill}")
        
        st.session_state.top_5_skills = st.session_state.comprehensive_skills
    
    col1, col2 = st.columns(2)

# Left column - JD Upload (only if no skills extracted yet)
with col1:
    if not st.session_state.get('comprehensive_skills'):
        st.header("Step 1: Upload Job Description")
        st.info("💡 Or upload JD in Technology Keywords tab to auto-extract skills")
    
    # Add mode selector
    skill_mode = st.radio(
        "How do you want to define skills?",
        ["Auto-extract from JD", "Manual entry"],
        horizontal=True
    )
    
    if skill_mode == "Auto-extract from JD":
        jd_file = st.file_uploader(
            "Upload JD (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="jd_file"
        )
        
        if jd_file:
            jd_text = extract_text_from_file(jd_file)
            
            if jd_text:
                # Apply JD masking if enabled
                if enable_jd_masking:
                    with st.spinner("🔒 Masking client-sensitive information..."):
                        jd_masking_result = st.session_state.masker.mask_jd(
                            jd_text, 
                            known_client_names=st.session_state.get('known_clients', [])
                        )
                        jd_text = jd_masking_result.masked_text
                        
                        # Log masking with filename
                        if jd_masking_result.mask_count > 0:
                            audit_entry = create_masking_audit_log(jd_masking_result, "jd")
                            audit_entry['filename'] = jd_file.name  # Add filename
                            st.session_state.masking_audit_log.append(audit_entry)
                            
                            st.success(f"🔒 Masked {jd_masking_result.mask_count} client-sensitive items from {jd_file.name}")
                
                with st.spinner("🔍 Extracting top 5 skills..."):
                    top_5_skills = st.session_state.validator.extract_top_5_skills(jd_text)
                    st.session_state.top_5_skills = top_5_skills
                
                st.success("✅ Top 5 Skills Extracted")
                
                st.subheader("🎯 Top 5 Critical Skills")
                
                # Show extracted skills with option to edit
                st.info("💡 You can edit these skills if needed")
                
                edited_skills = []
                for i, skill in enumerate(top_5_skills, 1):
                    edited_skill = st.text_input(
                        f"Skill {i}",
                        value=skill,
                        key=f"edit_skill_{i}"
                    )
                    edited_skills.append(edited_skill)
                
                # Update with edited skills
                if st.button("✅ Confirm Skills", key="confirm_auto"):
                    st.session_state.top_5_skills = edited_skills
                    st.success("Skills confirmed!")
    
    else:  # Manual entry mode
        st.info("✍️ Enter 1-5 skills you want to validate (flexible)")
        
        manual_skills = []
        
        st.subheader("🎯 Enter Skills (1-5)")
        
        # Provide some examples
        with st.expander("💡 Examples of good skill descriptions"):
            st.markdown("""
            **Good examples:**
            - GenAI implementation literacy (prompting, RAG, evaluation)
            - Product/Program execution (PRDs, stakeholder management)
            - Regulated domain experience (pharma/healthcare)
            - Data Engineering (ETL, data warehousing, SQL optimization)
            - Cloud Infrastructure (AWS/Azure, DevOps, scaling)
            
            **Keep skills:**
            - Comprehensive (not just "Python" or "SQL")
            - Specific to the role
            - 5-15 words each
            
            **You can enter 1-5 skills** - doesn't have to be exactly 5!
            """)
        
        for i in range(1, 6):
            skill = st.text_input(
                f"Skill {i} {'(Required)' if i == 1 else '(Optional)'}",
                placeholder=f"e.g., Technical skill or competency {i}",
                key=f"manual_skill_{i}"
            )
            if skill:
                manual_skills.append(skill)
        
        if len(manual_skills) >= 1:  # Changed from == 5 to >= 1
            if st.button("✅ Confirm Skills", key="confirm_manual"):
                st.session_state.top_5_skills = manual_skills
                st.success(f"✅ {len(manual_skills)} skill(s) confirmed!")
                
                # Display confirmed skills
                st.subheader("Confirmed Skills:")
                for i, skill in enumerate(manual_skills, 1):
                    st.write(f"**{i}.** {skill}")
        elif manual_skills:
            st.info(f"ℹ️ {len(manual_skills)} skill(s) entered. You can add more or click Confirm.")
        else:
            st.warning("⚠️ Please enter at least 1 skill to continue")

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
                # Extract candidate name before masking
                first_line = resume_text.split('\n')[0].strip()
                candidate_name = first_line if len(first_line) < 50 else "Candidate"
                
                # Apply PII masking if enabled
                if enable_pii_masking:
                    with st.spinner("🔒 Masking PII..."):
                        masking_result = st.session_state.masker.mask_resume(resume_text)
                        resume_text = masking_result.masked_text
                        
                        # Log masking with filename
                        if masking_result.mask_count > 0:
                            audit_entry = create_masking_audit_log(masking_result, "resume")
                            audit_entry['filename'] = resume_file.name  # Add filename
                            audit_entry['candidate_name'] = candidate_name  # Add candidate name
                            st.session_state.masking_audit_log.append(audit_entry)
                            
                            st.success(f"🔒 Masked {masking_result.mask_count} PII items from {resume_file.name}")
                
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
    total_skills = len(st.session_state.top_5_skills)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Skills with Projects", f"{validated_count}/{total_skills}")
    col2.metric("Average Score", f"{fit_score:.0f}%")
    col3.metric("Skills Missing Projects", f"{total_skills - validated_count}/{total_skills}")
    
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

# ==================== TAB 2: TECHNOLOGY KEYWORDS ====================
with main_tabs[1]:
    st.header("🔧 Skills for Validation Extraction")
    st.caption("Extract technology-specific keywords from Job Description")
    
    # Check if JD already uploaded
    if st.session_state.stored_jd_text and st.session_state.tech_keywords_result:
        st.success(f"✅ Using stored JD: {st.session_state.stored_jd_filename}")
        
        # Display stored results
        tech_keywords = st.session_state.tech_keywords_result
        
        st.success(f"✅ Extracted {len(tech_keywords)} technology keywords!")
        
        # Display keywords (categorized)
        st.subheader("🔧 Technology Keywords")
        
        categories = {
            "AI/ML": ["genai", "rag", "llm", "ml", "ai", "machine learning", "deep learning", "nlp", "gpt"],
            "Cloud": ["aws", "azure", "gcp", "cloud", "s3", "ec2", "lambda"],
            "Languages": ["python", "java", "javascript", "typescript", "go", "rust", "c++", "c#"],
            "Databases": ["sql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch"],
            "DevOps": ["docker", "kubernetes", "k8s", "jenkins", "ci/cd", "terraform", "ansible"],
            "Frameworks": ["react", "django", "flask", "fastapi", "spring", "node", "express"],
            "Other": []
        }
        
        categorized = {cat: [] for cat in categories.keys()}
        
        for keyword in tech_keywords:
            keyword_lower = keyword.lower()
            categorized_flag = False
            
            for category, markers in categories.items():
                if category != "Other" and any(marker in keyword_lower for marker in markers):
                    categorized[category].append(keyword)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                categorized["Other"].append(keyword)
        
        # Display by category
        for category, keywords in categorized.items():
            if keywords:
                with st.expander(f"📂 {category} ({len(keywords)})", expanded=True):
                    cols = st.columns(3)
                    for idx, kw in enumerate(keywords):
                        cols[idx % 3].write(f"• {kw}")
        
        # Export options
        st.divider()
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            keywords_csv = ", ".join(tech_keywords)
            st.download_button(
                label="📄 Download as Text",
                data=keywords_csv,
                file_name="tech_keywords.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col_exp2:
            keywords_json = json.dumps(tech_keywords, indent=2)
            st.download_button(
                label="📄 Download as JSON",
                data=keywords_json,
                file_name="tech_keywords.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Option to upload new JD
        st.divider()
        if st.button("📤 Upload Different JD", use_container_width=True):
            st.session_state.stored_jd_text = None
            st.session_state.stored_jd_filename = None
            st.session_state.tech_keywords_result = None
            st.session_state.jd_summary_result = None
            st.rerun()
    
    else:
        # JD upload for keyword extraction
        st.subheader("Step 1: Upload Job Description")
        
        tech_jd_file = st.file_uploader(
            "Upload JD (PDF/DOCX/TXT)",
            type=["pdf", "docx", "txt"],
            key="tech_jd_file",
            help="Upload JD to extract technology keywords"
        )
        
        if tech_jd_file:
            tech_jd_text = extract_text_from_file(tech_jd_file)
        else: tech_jd_text = None
        
        if tech_jd_text:
            # Apply JD masking if enabled
            if enable_jd_masking:
                jd_masking_result = st.session_state.masker.mask_jd(
                    tech_jd_text, 
                    known_client_names=st.session_state.get('known_clients', [])
                )
                tech_jd_text = jd_masking_result.masked_text
            
            with st.spinner("🔍 Extracting technology keywords..."):
                # Use LLM to extract tech keywords
                if st.session_state.validator.use_llm:
                    try:
                        prompt = f"""Extract ONLY technology-related keywords from this job description.

JOB DESCRIPTION:
{tech_jd_text[:3000]}

Focus on:
- Programming languages (Python, Java, etc.)
- Cloud platforms (AWS, Azure, GCP)
- Frameworks (React, Django, etc.)
- Tools & Technologies (Docker, Kubernetes, etc.)
- AI/ML technologies (GenAI, RAG, LLM, etc.)
- Databases (SQL, MongoDB, etc.)
- DevOps tools (Jenkins, Git, etc.)

Return ONLY a JSON array of technology keywords (10-20 items):
["keyword1", "keyword2", "keyword3", ...]

Just the array, nothing else:"""

                        from groq import Groq
                        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                        
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.1,
                            max_tokens=500
                        )
                        
                        result = response.choices[0].message.content.strip()
                        
                        # Parse JSON
                        if "```" in result:
                            result = re.search(r'```(?:json)?\s*(.*?)\s*```', result, re.DOTALL).group(1)
                        
                        tech_keywords = json.loads(result)
                        
                        # Store in session state for reuse
                        st.session_state.stored_jd_text = tech_jd_text
                        st.session_state.stored_jd_filename = tech_jd_file.name
                        st.session_state.tech_keywords_result = tech_keywords
                        
                        # Also generate JD summary and comprehensive skills immediately
                        with st.spinner("🤖 Generating JD summary and extracting skills..."):
                            try:
                                # Generate JD Summary
                                summary_prompt = f"""Analyze this job description and provide a comprehensive summary for recruiters.

JOB DESCRIPTION:
{tech_jd_text[:4000]}

Provide the following in JSON format:
1. role_summary: Brief 2-3 sentence summary of the role
2. key_requirements: List of 5-7 must-have skills/qualifications
3. ideal_candidate: Description of who would be perfect for this role
4. role_combination: What combination of roles this requires (e.g., "Data Engineer + Data Analyst")
5. experience_level: Years of experience needed
6. naukri_searches: 5 keyword combination strings for Naukri.com
7. linkedin_searches: 5 boolean search strings for LinkedIn

Return ONLY valid JSON:
{{
  "role_summary": "...",
  "key_requirements": ["...", "..."],
  "ideal_candidate": "...",
  "role_combination": "...",
  "experience_level": "5-7 years",
  "naukri_searches": ["...", "..."],
  "linkedin_searches": ["...", "..."]
}}"""

                                summary_response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role": "user", "content": summary_prompt}],
                                    temperature=0.2,
                                    max_tokens=2000
                                )
                                
                                summary_result = summary_response.choices[0].message.content.strip()
                                if "```json" in summary_result:
                                    summary_result = re.search(r'```json\s*(.*?)\s*```', summary_result, re.DOTALL).group(1)
                                elif "```" in summary_result:
                                    summary_result = re.search(r'```\s*(.*?)\s*```', summary_result, re.DOTALL).group(1)
                                
                                st.session_state.jd_summary_result = json.loads(summary_result)
                                
                                # Extract comprehensive skills for validation
                                st.session_state.comprehensive_skills = st.session_state.validator.extract_top_5_skills(tech_jd_text)
                                
                                st.success("✅ All analyses complete! Check all tabs.")
                                
                            except Exception as e:
                                st.warning(f"Note: Tech keywords extracted, but summary generation had an issue: {e}")
                        
                        st.success(f"✅ Extracted {len(tech_keywords)} technology keywords!")
                        
                        # Display keywords
                        st.subheader("🔧 Technology Keywords")
                        
                        # Group by category (simple heuristic)
                        categories = {
                            "AI/ML": ["genai", "rag", "llm", "ml", "ai", "machine learning", "deep learning", "nlp", "gpt"],
                            "Cloud": ["aws", "azure", "gcp", "cloud", "s3", "ec2", "lambda"],
                            "Languages": ["python", "java", "javascript", "typescript", "go", "rust", "c++", "c#"],
                            "Databases": ["sql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch"],
                            "DevOps": ["docker", "kubernetes", "k8s", "jenkins", "ci/cd", "terraform", "ansible"],
                            "Frameworks": ["react", "django", "flask", "fastapi", "spring", "node", "express"],
                            "Other": []
                        }
                        
                        categorized = {cat: [] for cat in categories.keys()}
                        
                        for keyword in tech_keywords:
                            keyword_lower = keyword.lower()
                            categorized_flag = False
                            
                            for category, markers in categories.items():
                                if category != "Other" and any(marker in keyword_lower for marker in markers):
                                    categorized[category].append(keyword)
                                    categorized_flag = True
                                    break
                            
                            if not categorized_flag:
                                categorized["Other"].append(keyword)
                        
                        # Display by category
                        for category, keywords in categorized.items():
                            if keywords:
                                with st.expander(f"📂 {category} ({len(keywords)})", expanded=True):
                                    cols = st.columns(3)
                                    for idx, kw in enumerate(keywords):
                                        cols[idx % 3].write(f"• {kw}")
                        
                        # Export keywords
                        st.divider()
                        st.subheader("📥 Export Keywords")
                        
                        # As comma-separated list
                        keywords_csv = ", ".join(tech_keywords)
                        
                        col_exp1, col_exp2 = st.columns(2)
                        
                        with col_exp1:
                            st.download_button(
                                label="📄 Download as Text",
                                data=keywords_csv,
                                file_name="tech_keywords.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        with col_exp2:
                            # As JSON
                            keywords_json = json.dumps(tech_keywords, indent=2)
                            st.download_button(
                                label="📄 Download as JSON",
                                data=keywords_json,
                                file_name="tech_keywords.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        
                        # Use as skills option
                        st.divider()
                        st.info("💡 Tip: You can use these keywords to validate resumes directly!")
                        
                        # Store in session state
                        st.session_state.extracted_tech_keywords = tech_keywords
                        
                        # Option to use for validation
                        if st.button("🎯 Use These Keywords for Validation", type="primary", use_container_width=True):
                            st.session_state.top_5_skills = tech_keywords[:5]  # Use top 5
                            st.success(f"✅ Loaded {len(st.session_state.top_5_skills)} keywords for validation!")
                            st.info("👉 Go to 'Skills Validation' tab to validate resumes")
                        
                        # Or select specific ones
                        st.divider()
                        st.subheader("🎯 Select Specific Keywords for Validation")
                        
                        selected_keywords = st.multiselect(
                            "Choose keywords to validate (1-10)",
                            tech_keywords,
                            max_selections=10,
                            help="Select which technology keywords you want to validate in resumes"
                        )
                        
                        if selected_keywords:
                            if st.button("✅ Use Selected Keywords", use_container_width=True):
                                st.session_state.top_5_skills = selected_keywords
                                st.success(f"✅ Loaded {len(selected_keywords)} keyword(s) for validation!")
                                st.info("👉 Go to 'Skills Validation' tab to validate resumes")
                        
                    except Exception as e:
                        st.error(f"Error extracting keywords: {e}")
                        st.info("Try uploading a different JD or check your API key")
                
                else:
                    # Fallback - regex extraction
                    st.warning("⚠️ LLM mode not available. Using simple keyword extraction.")
                    
                    common_tech = [
                        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
                        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "K8s",
                        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
                        "React", "Django", "Flask", "FastAPI", "Node.js",
                        "GenAI", "RAG", "LLM", "GPT", "Machine Learning", "ML",
                        "CI/CD", "Jenkins", "Git", "Terraform", "Ansible"
                    ]
                    
                    found_tech = [tech for tech in common_tech if tech.lower() in tech_jd_text.lower()]
                    
                    st.success(f"✅ Found {len(found_tech)} technology keywords!")
                    
                    st.subheader("🔧 Technology Keywords")
                    cols = st.columns(3)
                    for idx, tech in enumerate(found_tech):
                        cols[idx % 3].write(f"• {tech}")

# ==================== TAB 3: JD SUMMARY & SEARCH STRINGS ====================
with main_tabs[2]:
    st.header("📋 JD Summary & Search String Generator")
    st.caption("Get AI-powered JD summary, ideal candidate profile, and search strings for Naukri/LinkedIn")
    
    # Check if JD already uploaded and summary generated
    if st.session_state.stored_jd_text and st.session_state.jd_summary_result:
        st.success(f"✅ Using stored JD: {st.session_state.stored_jd_filename}")
        
        # Display stored summary results
        summary_data = st.session_state.jd_summary_result
        
        st.success("✅ JD Analysis Complete!")
        
        # Role Summary
        st.subheader("📋 Role Summary")
        st.info(summary_data.get("role_summary", "No summary available"))
        
        # Two column layout
        col_sum1, col_sum2 = st.columns([1, 1])
        
        with col_sum1:
            st.subheader("🎯 Key Requirements")
            for req in summary_data.get("key_requirements", []):
                st.write(f"• {req}")
            
            st.divider()
            
            st.subheader("⏱️ Experience Level")
            st.metric("Required Experience", summary_data.get("experience_level", "N/A"))
        
        with col_sum2:
            st.subheader("👤 Ideal Candidate Profile")
            st.write(summary_data.get("ideal_candidate", "N/A"))
        
        st.divider()
        
        # Role Combination - Highlighted
        st.subheader("🔄 Role Combination")
        st.success(f"### {summary_data.get('role_combination', 'N/A')}")
        st.caption("💡 Use this combination when searching for candidates on job portals")
        
        st.divider()
        
        # Search Strings
        st.subheader("🔍 Recruiter Search Strings")
        
        col_search1, col_search2 = st.columns(2)
        
        with col_search1:
            st.markdown("### 🟢 Naukri.com")
            st.caption("Keyword combinations for Naukri advanced search")
            
            for i, search in enumerate(summary_data.get("naukri_searches", []), 1):
                with st.expander(f"Search String {i}", expanded=i==1):
                    st.code(search, language=None)
                    st.caption(f"Copy this and paste in Naukri search box")
        
        with col_search2:
            st.markdown("### 🔵 LinkedIn")
            st.caption("Boolean search strings for LinkedIn Recruiter")
            
            for i, search in enumerate(summary_data.get("linkedin_searches", []), 1):
                with st.expander(f"Search String {i}", expanded=i==1):
                    st.code(search, language=None)
                    st.caption(f"Use in LinkedIn Recruiter search")
        
        st.divider()
        
        # Export
        st.subheader("📥 Export Summary")
        
        col_exp1, col_exp2 = st.columns(2)
        
        # Markdown export
        summary_md = f"""# JD Summary & Search Strings

## Role Summary
{summary_data.get('role_summary', '')}

## Role Combination
**{summary_data.get('role_combination', '')}**

## Experience Level
{summary_data.get('experience_level', '')}

## Key Requirements
{chr(10).join(f'- {req}' for req in summary_data.get('key_requirements', []))}

## Ideal Candidate Profile
{summary_data.get('ideal_candidate', '')}

## Naukri.com Search Strings
{chr(10).join(f'{i}. `{s}`' for i, s in enumerate(summary_data.get('naukri_searches', []), 1))}

## LinkedIn Search Strings
{chr(10).join(f'{i}. `{s}`' for i, s in enumerate(summary_data.get('linkedin_searches', []), 1))}
"""
        
        with col_exp1:
            st.download_button(
                label="📄 Download Summary (MD)",
                data=summary_md,
                file_name=f"jd_summary_{st.session_state.stored_jd_filename.split('.')[0]}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        # JSON export
        with col_exp2:
            summary_json = json.dumps(summary_data, indent=2)
            st.download_button(
                label="📄 Download Data (JSON)",
                data=summary_json,
                file_name=f"jd_data_{st.session_state.stored_jd_filename.split('.')[0]}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Option to upload new JD
        st.divider()
        if st.button("📤 Upload Different JD", key="jd_summary_new_upload", use_container_width=True):
            st.session_state.stored_jd_text = None
            st.session_state.stored_jd_filename = None
            st.session_state.tech_keywords_result = None
            st.session_state.jd_summary_result = None
            st.rerun()
    
    else:
        # Use stored JD if available
        if st.session_state.stored_jd_text:
            st.info(f"📄 Using JD: {st.session_state.stored_jd_filename}")
            
            if st.button("🚀 Generate JD Summary", use_container_width=True, type="primary"):
                jd_summary_text = st.session_state.stored_jd_text
                
                with st.spinner("🤖 Analyzing JD and generating search strings..."):
                    if st.session_state.validator.use_llm:
                        try:
                            from groq import Groq
                            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                            
                            prompt = f"""Analyze this job description and provide a comprehensive summary for recruiters.

JOB DESCRIPTION:
{jd_summary_text[:4000]}

Provide the following in JSON format:
1. role_summary: Brief 2-3 sentence summary of the role
2. key_requirements: List of 5-7 must-have skills/qualifications
3. ideal_candidate: Description of who would be perfect for this role (background, experience type)
4. role_combination: What combination of roles this requires (e.g., "Data Engineer + Data Analyst", "Product Manager + Technical Lead", "Backend Engineer + DevOps")
5. experience_level: Years of experience needed
6. naukri_searches: 5 keyword combination strings optimized for Naukri.com search
7. linkedin_searches: 5 boolean search strings optimized for LinkedIn Recruiter

Example role_combination:
- "Data Engineer + Business Analyst"
- "Product Manager + AI/ML Product Owner"
- "Full Stack Developer + Cloud Architect"

Example search strings:
Naukri: "Python AWS Data Engineer", "ETL Spark Databricks"
LinkedIn: "(Data Engineer OR ETL Developer) AND (AWS OR Azure) AND Python"

Return ONLY valid JSON:
{{
  "role_summary": "...",
  "key_requirements": ["...", "..."],
  "ideal_candidate": "...",
  "role_combination": "...",
  "experience_level": "5-7 years",
  "naukri_searches": ["...", "..."],
  "linkedin_searches": ["...", "..."]
}}"""

                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.2,
                                max_tokens=2000
                            )
                            
                            result = response.choices[0].message.content.strip()
                            
                            # Parse JSON
                            if "```json" in result:
                                result = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL).group(1)
                            elif "```" in result:
                                result = re.search(r'```\s*(.*?)\s*```', result, re.DOTALL).group(1)
                            
                            summary_data = json.loads(result)
                            
                            # Store in session state for reuse
                            st.session_state.jd_summary_result = summary_data
                            
                            # Display results
                            st.success("✅ Analysis Complete!")
                            
                            # Role Summary
                            st.subheader("📋 Role Summary")
                            st.info(summary_data.get("role_summary", "No summary available"))
                            
                            # Two column layout
                            col_sum1, col_sum2 = st.columns([1, 1])
                            
                            with col_sum1:
                                st.subheader("🎯 Key Requirements")
                                for req in summary_data.get("key_requirements", []):
                                    st.write(f"• {req}")
                                
                                st.divider()
                                
                                st.subheader("⏱️ Experience Level")
                                st.metric("Required Experience", summary_data.get("experience_level", "N/A"))
                            
                            with col_sum2:
                                st.subheader("👤 Ideal Candidate Profile")
                                st.write(summary_data.get("ideal_candidate", "N/A"))
                            
                            st.divider()
                            
                            # Role Combination - Highlighted
                            st.subheader("🔄 Role Combination")
                            st.success(f"### {summary_data.get('role_combination', 'N/A')}")
                            st.caption("💡 Use this combination when searching for candidates on job portals")
                            
                            st.divider()
                            
                            # Search Strings
                            st.subheader("🔍 Recruiter Search Strings")
                            
                            col_search1, col_search2 = st.columns(2)
                            
                            with col_search1:
                                st.markdown("### 🟢 Naukri.com")
                                st.caption("Keyword combinations for Naukri advanced search")
                                
                                for i, search in enumerate(summary_data.get("naukri_searches", []), 1):
                                    with st.expander(f"Search String {i}", expanded=i==1):
                                        st.code(search, language=None)
                                        st.caption(f"Copy this and paste in Naukri search box")
                            
                            with col_search2:
                                st.markdown("### 🔵 LinkedIn")
                                st.caption("Boolean search strings for LinkedIn Recruiter")
                                
                                for i, search in enumerate(summary_data.get("linkedin_searches", []), 1):
                                    with st.expander(f"Search String {i}", expanded=i==1):
                                        st.code(search, language=None)
                                        st.caption(f"Use in LinkedIn Recruiter search")
                            
                            st.divider()
                            
                            # Export
                            st.subheader("📥 Export Summary")
                            
                            col_exp1, col_exp2 = st.columns(2)
                            
                            # Markdown export
                            summary_md = f"""# JD Summary & Search Strings

## Role Summary
{summary_data.get('role_summary', '')}

## Role Combination
**{summary_data.get('role_combination', '')}**

## Experience Level
{summary_data.get('experience_level', '')}

## Key Requirements
{chr(10).join(f'- {req}' for req in summary_data.get('key_requirements', []))}

## Ideal Candidate Profile
{summary_data.get('ideal_candidate', '')}

## Naukri.com Search Strings
{chr(10).join(f'{i}. `{s}`' for i, s in enumerate(summary_data.get('naukri_searches', []), 1))}

## LinkedIn Search Strings
{chr(10).join(f'{i}. `{s}`' for i, s in enumerate(summary_data.get('linkedin_searches', []), 1))}
"""
                            
                            with col_exp1:
                                st.download_button(
                                    label="📄 Download Summary (MD)",
                                    data=summary_md,
                                    file_name=f"jd_summary_{st.session_state.stored_jd_filename.split('.')[0]}.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                            
                            # JSON export
                            with col_exp2:
                                summary_json = json.dumps(summary_data, indent=2)
                                st.download_button(
                                    label="📄 Download Data (JSON)",
                                    data=summary_json,
                                    file_name=f"jd_data_{st.session_state.stored_jd_filename.split('.')[0]}.json",
                                    mime="application/json",
                                    use_container_width=True
                                )
                        
                        except Exception as e:
                            st.error(f"Error analyzing JD: {e}")
                            st.info("💡 Make sure your GROQ_API_KEY is set correctly")
                    
                    else:
                        st.warning("⚠️ LLM mode required for this feature")
                        st.info("Please set GROQ_API_KEY environment variable to use JD Summary feature")
        
        else:
            # No stored JD - prompt upload
            st.info("💡 Please upload JD in the Technology Keywords tab first, or upload here:")
            
            jd_summary_file = st.file_uploader(
                "Upload Job Description",
                type=["pdf", "docx", "txt"],
                key="jd_summary_file",
                help="Upload JD to get summary and search strings"
            )
            
            if jd_summary_file:
                jd_summary_text = extract_text_from_file(jd_summary_file)
                
                if jd_summary_text:
                    # Store JD
                    st.session_state.stored_jd_text = jd_summary_text
                    st.session_state.stored_jd_filename = jd_summary_file.name
                    
                    st.success(f"✅ JD uploaded! Click the button above to generate summary.")
                    st.rerun()


# ==================== TAB 4: HOW IT WORKS ====================
with main_tabs[3]:
    st.header("ℹ️ How This Tool Works")
    
    st.markdown("""
    ## 🔍 Semantic Search & Validation
    
    ### What is Semantic Search?
    
    **Yes, we use semantic search!** The tool uses multiple layers of intelligence:
    
    #### 1. **Skill Extraction (JD Analysis)**
    - **LLM-powered**: Uses AI to understand context and extract meaningful skills
    - **Semantic understanding**: Not just keyword matching
    - Example: "GenAI implementation literacy" is extracted as a complete concept, not just "GenAI"
    
    #### 2. **Skill Matching (Resume Validation)**
    - **Semantic matching**: Finds related terms even if not exact
    - **Context-aware**: Looks at surrounding text, not just isolated keywords
    - Example: If JD says "RAG", we match "Retrieval Augmented Generation", "RAG architecture", "RAG-based systems"
    
    #### 3. **Evidence Validation**
    - **Project detection**: Identifies actual project work vs. skill lists
    - **Outcome recognition**: Finds quantified results (reduced by X%, improved Y)
    - **Action verb analysis**: Distinguishes "built" vs "familiar with"
    
    ### How Semantic Matching Works
    
    ```
    JD Skill: "GenAI implementation"
    
    Resume matches:
    ✅ "Generative AI solutions"
    ✅ "Gen AI-based audit tool"
    ✅ "LLM implementation"
    ✅ "AI/ML implementation"
    
    Resume doesn't match:
    ❌ "Artificial Intelligence research" (different context)
    ❌ "AI training data" (different aspect)
    ```
    
    ### Validation Scoring
    
    Each skill gets 0-100% score based on:
    
    1. **Found in resume** (0-20 points)
       - Skill mentioned: 20 points
       - Not found: 0 points
    
    2. **Project evidence** (0-50 points)
       - Clear project with outcomes: 50 points
       - Project mentioned but vague: 30 points
       - Just listed in skills: 10 points
    
    3. **Evidence quality** (0-30 points)
       - Action verbs (built, led, designed): 15 points
       - Quantified outcomes (%, time, cost): 15 points
    
    **Example:**
    ```
    Skill: "Python"
    
    Resume says: "Built Python microservices reducing latency by 40%"
    
    Score breakdown:
    - Found: 20 ✓
    - Project: 50 ✓ (clear project with outcomes)
    - Quality: 30 ✓ (action verb "built" + metric "40%")
    Total: 100/100
    ```
    
    ### Technology Keywords Tab
    
    The **Technology Keywords** tab:
    - Extracts only technology-specific terms
    - Focuses on tools, languages, frameworks
    - Useful for quick tech stack overview
    - Can be used to manually define validation skills
    
    ### Security Features
    
    - **PII Masking**: Removes personal info BEFORE validation
    - **Client Masking**: Protects confidential JD info
    - **Semantic search still works**: Masking doesn't affect skill matching
    - **Audit trail**: All masking operations logged
    
    ### Why This Approach?
    
    ✅ **Better than keyword matching**: Understands synonyms and context
    ✅ **Better than exact matching**: Finds related concepts
    ✅ **Evidence-based**: Validates actual work, not just claims
    ✅ **Semantic understanding**: Like a human recruiter would read
    
    ### Limitations
    
    ⚠️ **Not perfect**: May miss creative phrasing
    ⚠️ **Context-dependent**: Works best with clear project descriptions
    ⚠️ **English-focused**: Optimized for English resumes
    
    ### Best Practices
    
    1. **Review evidence**: Don't rely solely on scores
    2. **Check examples**: Look at project evidence found
    3. **Use interview questions**: Validate weak skills in person
    4. **Compare candidates**: Side-by-side evaluation
    
    ---
    
    ## 🎯 Summary
    
    **This tool uses:**
    - ✅ Semantic search and matching
    - ✅ AI-powered skill extraction
    - ✅ Context-aware validation
    - ✅ Evidence-based scoring
    - ✅ Project experience detection
    
    **Not just keyword search!** 🚀
    """)

# Footer
st.divider()

# Security audit section
if st.session_state.masking_audit_log:
    with st.expander("🔒 Security Audit Log", expanded=False):
        st.write(f"**Total masking operations:** {len(st.session_state.masking_audit_log)}")
        
        # Summary by type
        resume_ops = len([log for log in st.session_state.masking_audit_log if log.get('document_type') == 'resume'])
        jd_ops = len([log for log in st.session_state.masking_audit_log if log.get('document_type') == 'jd'])
        
        col_sum1, col_sum2 = st.columns(2)
        col_sum1.metric("Resume Operations", resume_ops)
        col_sum2.metric("JD Operations", jd_ops)
        
        st.divider()
        
        # Detailed log
        import pandas as pd
        audit_df = pd.DataFrame(st.session_state.masking_audit_log)
        
        # Format for display
        if not audit_df.empty:
            # Add human-readable columns safely
            display_df = pd.DataFrame()
            
            if 'timestamp' in audit_df.columns:
                display_df['Timestamp'] = pd.to_datetime(audit_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            if 'filename' in audit_df.columns:
                display_df['File Name'] = audit_df['filename']
            
            if 'candidate_name' in audit_df.columns:
                display_df['Candidate'] = audit_df['candidate_name'].fillna('-')
            
            if 'document_type' in audit_df.columns:
                display_df['Type'] = audit_df['document_type'].str.upper()
            
            if 'mask_count' in audit_df.columns:
                display_df['Items Masked'] = audit_df['mask_count']
            elif 'count' in audit_df.columns:
                display_df['Items Masked'] = audit_df['count']
            
            # Add sensitivity info if available (as a summary)
            if 'sensitivity_detected' in audit_df.columns:
                # Convert dict to readable string
                def format_sensitivity(val):
                    if isinstance(val, dict):
                        return ', '.join([f"{k}:{v}" for k, v in val.items()])
                    return str(val)
                
                display_df['What Was Masked'] = audit_df['sensitivity_detected'].apply(format_sensitivity)
            
            # Display whatever columns we have
            if not display_df.empty:
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(audit_df, use_container_width=True, hide_index=True)
            
            # Export audit log
            csv_data = audit_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Audit Log (CSV)",
                data=csv_data,
                file_name=f"security_audit_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

st.caption("🎯 Simple JobFit Analyzer | Top 5 Skills Validation | 🔒 PII & Client Data Protected")
