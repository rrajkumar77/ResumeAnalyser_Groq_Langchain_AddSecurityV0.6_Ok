"""
Simplified Top-5 Skills Validator  (Cost-Optimised)
====================================================

Optimisations vs original:
1. BATCH validation  – all skills validated in ONE LLM call (was 5 calls)
2. Smaller model     – llama-3.1-8b-instant for validation (was 70b-versatile)
3. Shorter prompts   – resume truncated to 2 000 chars (was 2 500 per call)
4. JD cache          – extract_top_5_skills result cached by JD hash
5. 70b only for JD   – skill extraction keeps the large model for accuracy

Token savings per candidate (approx):
  Before : 1x(4000+400) + 5x(2500+300)  ~= 18 400 tokens
  After  : 1x(4000+400) + 1x(2000+900)  ~=  7 300 tokens  (-60%)
"""

import os
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from groq import Groq

from semantic_validator_optimized import (
    EnhancedResumeValidator,
    CandidateValidationReport,
    JDSummary,
    SkillPriority,
    JDSkill,
)


@dataclass
class SimpleSkillValidation:
    """Simple skill validation result"""
    skill_name: str
    has_project_experience: bool
    validation_score: float        # 0-100
    evidence_summary: str
    project_example: str


class SimpleTop5Validator:
    """
    Extracts TOP 5 skills from JD and validates against resume.
    Works with ANY JD format.
    """

    # Large model: nuanced JD understanding (used once per JD)
    _JD_MODEL = "llama-3.3-70b-versatile"
    # Small/fast model: structured JSON extraction for validation
    _VAL_MODEL = "llama-3.1-8b-instant"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

        if not self.api_key:
            self.use_llm = False
            self.fallback_validator = EnhancedResumeValidator()
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                self.use_llm = True
            except Exception:
                self.use_llm = False
                self.fallback_validator = EnhancedResumeValidator()

        # Cache: avoid re-calling LLM for the same JD
        self._jd_cache: Dict[int, List[str]] = {}

    # ------------------------------------------------------------------
    # JD SKILL EXTRACTION  (large model, cached per JD)
    # ------------------------------------------------------------------

    def extract_top_5_skills(self, jd_text: str) -> List[str]:
        """
        Extract the TOP 5 most critical skills from JD.
        Cached by JD hash – safe to call multiple times per session.
        """
        cache_key = hash(jd_text[:2000])
        if cache_key in self._jd_cache:
            print("CACHED JD skills returned (no LLM call)")
            return self._jd_cache[cache_key]

        if not self.use_llm:
            result = self._fallback_extract_skills(jd_text)
            self._jd_cache[cache_key] = result
            return result

        try:
            prompt = f"""Read this job description and extract the TOP 5 most critical skills/competencies needed.

JOB DESCRIPTION:
{jd_text[:4000]}

IMPORTANT RULES:
1. Frame each skill as a DEMONSTRABLE COMPETENCY — what a candidate must be able to show evidence of doing.
2. Use broad enough language to capture transferable experience (e.g. "Stakeholder management and influencing senior leaders" not "AI executive sponsorship")
3. Each skill should be 5-15 words and describe the CAPABILITY, not just the domain.
4. Good examples:
   - "Driving adoption of new platforms or processes across large organisations"
   - "Stakeholder management and influencing at senior/executive level"
   - "Designing training, workshops or enablement programs for teams"
   - "Measuring outcomes and impact of initiatives with data"
5. Bad examples (too narrow/literal):
   - "AI adoption strategy" (too specific — misses transferable change management experience)
   - "GenAI" (just a tool name)
   - "Executive AI sponsorship" (too domain-locked)

Return as JSON array with EXACTLY 5 skills:
["Competency 1", "Competency 2", "Competency 3", "Competency 4", "Competency 5"]

Just the array, nothing else:"""

            response = self.client.chat.completions.create(
                model=self._JD_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=400,
            )

            result_text = response.choices[0].message.content.strip()
            if "```" in result_text:
                result_text = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", result_text, re.DOTALL
                ).group(1)

            skills = json.loads(result_text)
            if isinstance(skills, list) and len(skills) >= 5:
                skills = skills[:5]
            else:
                skills = self._fallback_extract_skills(jd_text)

        except Exception as e:
            print(f"LLM skill extraction failed: {e}")
            skills = self._fallback_extract_skills(jd_text)

        self._jd_cache[cache_key] = skills
        return skills

    # ------------------------------------------------------------------
    # CANDIDATE VALIDATION  (small model, BATCHED – 1 call for all skills)
    # ------------------------------------------------------------------

    def validate_candidate(
        self,
        top_5_skills: List[str],
        resume_text: str,
        candidate_name: str = "Candidate",
    ) -> Tuple[float, List[SimpleSkillValidation]]:
        """
        Validate candidate against all skills in a SINGLE LLM call.
        Returns: (fit_score 0-100, validations list)
        """
        if not top_5_skills:
            return 0.0, []

        if not self.use_llm:
            return self._fallback_validate_all(top_5_skills, resume_text)

        validations = self._validate_all_skills_batched(top_5_skills, resume_text)
        fit_score = (
            sum(v.validation_score for v in validations) / len(validations)
            if validations else 0.0
        )
        return fit_score, validations

    def _validate_all_skills_batched(
        self, skills: List[str], resume_text: str
    ) -> List[SimpleSkillValidation]:
        """
        ONE LLM call evaluates all skills.
        Uses the large 70b model to correctly handle semantic bridging —
        especially important for career-transition candidates whose resume
        language differs from the JD but whose experience is genuinely transferable.
        """
        skills_numbered = "\n".join(
            f"{i + 1}. {skill}" for i, skill in enumerate(skills)
        )

        prompt = f"""You are an expert recruiter assessing a candidate's resume against required skills.

RESUME:
{resume_text[:2500]}

SKILLS TO EVALUATE:
{skills_numbered}

CRITICAL INSTRUCTIONS:
1. Look for DIRECT experience AND transferable/adjacent experience.
   e.g. "AI adoption strategy" can be evidenced by "driving adoption of new compliance frameworks"
   e.g. "Stakeholder buy-in" can be evidenced by "partnered with cross-functional teams on X"
   e.g. "Change management" can be evidenced by "redesigned protocols reducing incidents by 15%"
2. Do NOT require the exact skill words to appear in the resume. Judge the SUBSTANCE of experience.
3. Give credit for measurable outcomes even if in a different domain.
4. A score of 0 should only be given when there is genuinely ZERO related experience.

Return a JSON array with one entry per skill (same order as the list):
[
  {{
    "skill": "exact skill name from list above",
    "has_project_experience": true,
    "score": 85,
    "evidence": "specific evidence from resume — quote actual phrases",
    "example": "one concrete example from resume, or 'No evidence found'"
  }}
]

Scoring guide:
- 80-100: Clear direct or transferable project experience with outcomes
- 50-79:  Relevant experience but vague or no outcomes stated
- 20-49:  Weak or tangential connection to the skill
- 0-19:   Genuinely no related experience found

Return ONLY the JSON array, no markdown fences:"""

        try:
            response = self.client.chat.completions.create(
                model=self._JD_MODEL,   # 70b for semantic bridging accuracy
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )

            result_text = response.choices[0].message.content.strip()
            if "```" in result_text:
                result_text = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", result_text, re.DOTALL
                ).group(1)

            data_list = json.loads(result_text)

            validations: List[SimpleSkillValidation] = []
            for i, skill in enumerate(skills):
                if i < len(data_list):
                    d = data_list[i]
                    validations.append(
                        SimpleSkillValidation(
                            skill_name=skill,
                            has_project_experience=bool(
                                d.get("has_project_experience", False)
                            ),
                            validation_score=float(d.get("score", 0)),
                            evidence_summary=d.get("evidence", ""),
                            project_example=d.get("example", "No evidence found"),
                        )
                    )
                else:
                    # LLM returned fewer items than skills – safe fallback
                    validations.append(self._fallback_validate_skill(skill, ""))

            return validations

        except Exception as e:
            print(f"Batched validation failed: {e}. Falling back to regex.")
            return self._fallback_validate_all_regex(skills, resume_text)

    # ------------------------------------------------------------------
    # FALLBACKS (no LLM)
    # ------------------------------------------------------------------

    def _fallback_extract_skills(self, jd_text: str) -> List[str]:
        """Keyword-based skill extraction when LLM is unavailable."""
        jd_lower = jd_text.lower()

        if "genai" in jd_lower and ("product" in jd_lower or "program" in jd_lower):
            return [
                "GenAI implementation literacy (prompting, RAG, evaluation frameworks)",
                "Product/Program execution (PRDs, stakeholder management, delivery)",
                "Regulated domain experience (pharma/healthcare/life sciences)",
                "Communication and structuring (requirements translation, stakeholder demos)",
                "Quality definition and adoption (rubrics, training, governance)",
            ]

        skill_patterns = {
            "product management": "Product Management (roadmap, stakeholder coordination, delivery)",
            "program management": "Program Management (cross-functional delivery, risk management)",
            "data science": "Data Science (ML models, analytics, data pipelines)",
            "software engineering": "Software Engineering (coding, architecture, deployment)",
            "cloud": "Cloud Infrastructure (AWS/Azure/GCP, DevOps, scaling)",
            "machine learning": "Machine Learning (model development, training, deployment)",
            "stakeholder": "Stakeholder Management (communication, alignment, leadership)",
            "agile": "Agile Methodology (sprint planning, delivery, collaboration)",
        }

        found: List[str] = []
        for keyword, label in skill_patterns.items():
            if keyword in jd_lower and label not in found:
                found.append(label)

        generic = [
            "Technical Proficiency (tools and technologies for the role)",
            "Domain Knowledge (industry-specific expertise)",
            "Project Delivery (end-to-end execution and results)",
            "Communication Skills (stakeholder engagement and documentation)",
            "Problem Solving (analytical thinking and solution design)",
        ]
        while len(found) < 5:
            for g in generic:
                if g not in found:
                    found.append(g)
                    break

        return found[:5]

    def _fallback_validate_all(
        self, skills: List[str], resume_text: str
    ) -> Tuple[float, List[SimpleSkillValidation]]:
        validations = [self._fallback_validate_skill(s, resume_text) for s in skills]
        fit_score = (
            sum(v.validation_score for v in validations) / len(validations)
            if validations else 0.0
        )
        return fit_score, validations

    def _fallback_validate_all_regex(
        self, skills: List[str], resume_text: str
    ) -> List[SimpleSkillValidation]:
        return [self._fallback_validate_skill(s, resume_text) for s in skills]

    def _fallback_validate_skill(
        self, skill: str, resume_text: str
    ) -> SimpleSkillValidation:
        """Simple keyword + action-verb matching (no LLM)."""
        skill_lower = skill.lower()
        resume_lower = resume_text.lower()

        if skill_lower not in resume_lower:
            return SimpleSkillValidation(
                skill_name=skill,
                has_project_experience=False,
                validation_score=0,
                evidence_summary="Not found in resume",
                project_example="No evidence found",
            )

        action_verbs = [
            "built", "developed", "led", "designed", "implemented",
            "created", "delivered", "shipped", "deployed",
        ]
        skill_pos = resume_lower.find(skill_lower)
        context = resume_lower[
            max(0, skill_pos - 200): min(len(resume_lower), skill_pos + 200)
        ]

        has_action = any(v in context for v in action_verbs)
        has_outcome = any(p in context for p in ["%", "reduced", "increased", "improved"])

        if has_action and has_outcome:
            return SimpleSkillValidation(
                skill_name=skill, has_project_experience=True, validation_score=75,
                evidence_summary="Found with action verbs and outcomes",
                project_example="See resume for details",
            )
        elif has_action:
            return SimpleSkillValidation(
                skill_name=skill, has_project_experience=True, validation_score=50,
                evidence_summary="Found with action verbs but no clear outcomes",
                project_example="See resume for details",
            )
        else:
            return SimpleSkillValidation(
                skill_name=skill, has_project_experience=False, validation_score=25,
                evidence_summary="Mentioned but no project context",
                project_example="See resume for details",
            )

    # ------------------------------------------------------------------
    # REPORT GENERATION  (zero LLM calls)
    # ------------------------------------------------------------------

    def generate_simple_report(
        self,
        candidate_name: str,
        top_5_skills: List[str],
        fit_score: float,
        validations: List[SimpleSkillValidation],
    ) -> str:
        """Generate clean markdown report."""
        md = f"""# Validation Report: {candidate_name}

## Overall Fit Score: {fit_score:.0f}/100

{"✅ **STRONG FIT**" if fit_score >= 75 else "⚠️ **CONDITIONAL FIT**" if fit_score >= 60 else "❌ **WEAK FIT**"}

---

## Top {len(validations)} Skills Assessment

"""
        for i, val in enumerate(validations, 1):
            icon = "✅" if val.has_project_experience else "❌"
            md += f"""### {i}. {icon} {val.skill_name} - {val.validation_score:.0f}%

**Has Project Experience**: {"Yes" if val.has_project_experience else "No"}

**Evidence**: {val.evidence_summary}

**Example**: {val.project_example}

---

"""
        validated_count = sum(1 for v in validations if v.has_project_experience)
        md += f"""## Summary

- **Skills with Project Experience**: {validated_count}/{len(validations)}
- **Average Validation Score**: {fit_score:.0f}%

## Recommendation

"""
        if fit_score >= 75:
            md += "✅ **PROCEED TO INTERVIEW** – Strong candidate with validated project experience\n"
        elif fit_score >= 60:
            md += "⚠️ **INTERVIEW WITH CAUTION** – Some gaps in project evidence. Ask targeted questions.\n"
        else:
            md += "❌ **NOT RECOMMENDED** – Insufficient project experience in key skills\n"

        return md


__all__ = ["SimpleTop5Validator", "SimpleSkillValidation"]
