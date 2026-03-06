"""
LLM-Powered JD Analyzer and Skill Matcher
==========================================

Uses Groq API to intelligently:
1. Parse JD into mandatory/desired/excluded skills
2. Match resume skills semantically 
3. Validate project evidence with context understanding
4. Extract timeline accurately

This replaces regex-based parsing with LLM intelligence.
"""

import os
import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from groq import Groq

# Import from base validator
from semantic_validator_optimized import (
    JDSkill,
    JDSummary,
    SkillPriority,
    SkillValidation,
    ExperienceType,
    ProjectEvidence,
    ExperienceTimeline,
    CandidateValidationReport
)


class LLMPoweredJDAnalyzer:
    """Use LLM to parse JD with intelligence instead of regex"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required for LLM-powered analysis")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def analyze_jd(self, jd_text: str) -> JDSummary:
        """Parse JD using LLM to extract skills intelligently"""
        
        prompt = f"""Analyze this job description and extract information in JSON format.

JOB DESCRIPTION:
{jd_text[:4000]}

Extract:
1. role_title: The job title/position
2. role_archetype: Type (e.g., "Product Manager", "Engineer", "Data Scientist")
3. core_problem: Main problem this role solves (2-3 sentences)
4. mandatory_skills: Array of must-have/required/non-negotiable skills
5. highly_desired_skills: Array of preferred/strong signals skills
6. good_to_have_skills: Array of nice-to-have/bonus skills
7. excluded_skills: Array of skills explicitly NOT wanted
8. required_experience_years: Minimum years required (number or null)
9. domain_requirements: Array of domain/industry requirements

IMPORTANT:
- For skills, extract complete phrases (e.g., "RAG basics" not just "RAG")
- Keep skills concise (2-8 words each)
- Don't split compound skills
- Exclude fragments and connecting words
- Focus on technical and business skills, not soft skills

Return ONLY valid JSON, no markdown or explanations:
{{
  "role_title": "...",
  "role_archetype": "...",
  "core_problem": "...",
  "mandatory_skills": ["skill1", "skill2"],
  "highly_desired_skills": ["skill3"],
  "good_to_have_skills": ["skill4"],
  "excluded_skills": ["skill5"],
  "required_experience_years": 5,
  "domain_requirements": ["pharma", "healthcare"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON if wrapped in markdown
            if "```json" in result_text:
                result_text = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            elif "```" in result_text:
                result_text = re.search(r'```\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            
            data = json.loads(result_text)
            
            # Convert to JDSummary
            summary = JDSummary(
                role_title=data.get("role_title", "Position"),
                role_archetype=data.get("role_archetype", "General"),
                core_problem=data.get("core_problem", "Not specified"),
                required_experience_years=data.get("required_experience_years"),
                domain_requirements=data.get("domain_requirements", [])
            )
            
            # Convert skills to JDSkill objects
            for skill_name in data.get("mandatory_skills", []):
                if skill_name and len(skill_name) > 2:
                    summary.mandatory_skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.MANDATORY,
                        keywords=self._generate_keywords(skill_name),
                        context="Mandatory/Must-Have"
                    ))
            
            for skill_name in data.get("highly_desired_skills", []):
                if skill_name and len(skill_name) > 2:
                    summary.highly_desired_skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.HIGHLY_DESIRED,
                        keywords=self._generate_keywords(skill_name),
                        context="Highly Desired"
                    ))
            
            for skill_name in data.get("good_to_have_skills", []):
                if skill_name and len(skill_name) > 2:
                    summary.good_to_have_skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.GOOD_TO_HAVE,
                        keywords=self._generate_keywords(skill_name),
                        context="Good-to-Have"
                    ))
            
            for skill_name in data.get("excluded_skills", []):
                if skill_name and len(skill_name) > 2:
                    summary.excluded_skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.EXCLUDED,
                        keywords=self._generate_keywords(skill_name),
                        context="Excluded/Not Looking For"
                    ))
            
            # Generate search keywords
            summary.search_keywords = self._generate_search_keywords(summary)
            summary.reject_keywords = self._generate_reject_keywords(summary)
            
            return summary
            
        except Exception as e:
            print(f"LLM parsing error: {e}")
            # Fallback to basic parsing
            return self._fallback_parsing(jd_text)
    
    def _generate_keywords(self, skill_name: str) -> List[str]:
        """Generate semantic keywords for skill"""
        keywords = [skill_name.lower()]
        skill_lower = skill_name.lower()
        
        # Common variations
        variants = {
            'genai': ['genai', 'gen ai', 'generative ai', 'llm', 'large language model'],
            'rag': ['rag', 'retrieval augmented', 'retrieval-augmented', 'vector search'],
            'prompt': ['prompting', 'prompt engineering', 'prompt design', 'prompt optimization'],
            'python': ['python', 'python3', 'py', 'python programming'],
            'aws': ['aws', 'amazon web services', 'amazon cloud'],
            'docker': ['docker', 'containerization', 'containers'],
            'kubernetes': ['kubernetes', 'k8s', 'container orchestration'],
            'pharma': ['pharma', 'pharmaceutical', 'life sciences', 'healthcare'],
        }
        
        for key, values in variants.items():
            if key in skill_lower:
                keywords.extend(values)
        
        return list(set(keywords))
    
    def _generate_search_keywords(self, summary: JDSummary) -> List[str]:
        """Generate search keywords from mandatory skills"""
        keywords = []
        for skill in summary.mandatory_skills[:10]:
            keywords.extend(skill.keywords[:3])
        return list(set(keywords))[:20]
    
    def _generate_reject_keywords(self, summary: JDSummary) -> List[str]:
        """Generate reject keywords from excluded skills"""
        keywords = []
        for skill in summary.excluded_skills[:5]:
            keywords.extend(skill.keywords[:2])
        return list(set(keywords))[:10]
    
    def _fallback_parsing(self, jd_text: str) -> JDSummary:
        """Fallback if LLM fails - basic parsing"""
        return JDSummary(
            role_title="Position",
            role_archetype="General",
            core_problem="See JD for details"
        )


class LLMPoweredSkillValidator:
    """Use LLM to validate skills with context understanding"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def validate_skill(
        self, 
        skill_name: str, 
        resume_text: str
    ) -> SkillValidation:
        """Use LLM to validate if candidate has real experience with skill"""
        
        prompt = f"""Analyze if this candidate has REAL PROJECT EXPERIENCE with "{skill_name}".

RESUME:
{resume_text[:3000]}

Evaluate:
1. Is "{skill_name}" mentioned or implied in the resume?
2. Is there PROJECT EVIDENCE (specific projects, outcomes, metrics)?
3. Or is it just listed as a skill without context?

Respond in JSON:
{{
  "found": true/false,
  "experience_type": "real_project" | "claimed_only" | "not_found",
  "validation_score": 0.0-1.0,
  "evidence_summary": "brief description of evidence found",
  "projects": [
    {{
      "project_name": "...",
      "evidence_strength": 0.0-1.0,
      "outcomes": ["outcome1", "outcome2"]
    }}
  ],
  "gap_analysis": "what's missing or weak",
  "interview_questions": ["question1", "question2"]
}}

SCORING GUIDE:
- real_project + outcomes + metrics = 0.8-1.0
- real_project but vague = 0.5-0.7
- just mentioned in skills section = 0.2-0.4
- not found = 0.0

Return ONLY valid JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if "```json" in result_text:
                result_text = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            elif "```" in result_text:
                result_text = re.search(r'```\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            
            data = json.loads(result_text)
            
            # Map to experience type
            exp_type_map = {
                "real_project": ExperienceType.REAL_PROJECT,
                "claimed_only": ExperienceType.CLAIMED_KNOWLEDGE,
                "not_found": ExperienceType.UNVALIDATED
            }
            
            experience_type = exp_type_map.get(
                data.get("experience_type", "not_found"),
                ExperienceType.UNVALIDATED
            )
            
            # Create validation result
            validation = SkillValidation(
                skill_name=skill_name,
                claimed_in_resume=data.get("found", False),
                experience_type=experience_type,
                validation_score=float(data.get("validation_score", 0.0)),
                gap_analysis=data.get("gap_analysis", ""),
                improvement_suggestions=data.get("interview_questions", [])
            )
            
            # Add project evidence
            for proj_data in data.get("projects", []):
                evidence = ProjectEvidence(
                    project_name=proj_data.get("project_name", "Project"),
                    role_in_project="See resume",
                    technologies_used=[skill_name],
                    outcomes=proj_data.get("outcomes", []),
                    evidence_strength=float(proj_data.get("evidence_strength", 0.5)),
                    evidence_type=experience_type
                )
                validation.evidence.append(evidence)
            
            return validation
            
        except Exception as e:
            print(f"LLM validation error for {skill_name}: {e}")
            # Fallback
            return SkillValidation(
                skill_name=skill_name,
                claimed_in_resume=False,
                experience_type=ExperienceType.UNVALIDATED,
                validation_score=0.0,
                gap_analysis=f"Could not validate {skill_name}"
            )


class LLMPoweredTimelineAnalyzer:
    """Use LLM to extract and analyze experience timeline"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def analyze_timeline(self, resume_text: str) -> ExperienceTimeline:
        """Use LLM to extract accurate timeline"""
        
        prompt = f"""Extract employment history and calculate total experience.

RESUME:
{resume_text[:3000]}

Extract each job with:
- Company name
- Role/title
- Start date (MM/YYYY or YYYY)
- End date (MM/YYYY or YYYY or "Present")
- Duration in years (calculate accurately)
- Type: "project_delivery" if shows actual projects/outcomes, "support" if maintenance/ops, "unclear" if vague

Respond in JSON:
{{
  "jobs": [
    {{
      "company": "...",
      "role": "...",
      "start": "MM/YYYY",
      "end": "MM/YYYY or Present",
      "duration_years": 2.5,
      "type": "project_delivery" | "support" | "unclear",
      "evidence": "brief description of what they did"
    }}
  ],
  "total_claimed": 6.9,
  "total_validated": 4.0,
  "validation_ratio": 0.58,
  "red_flags": ["flag1 if any"]
}}

VALIDATION RULES:
- project_delivery: Has specific projects with outcomes
- support: Maintenance, operations, helpdesk work
- unclear: Vague descriptions or gaps

Calculate duration_years ACCURATELY using months difference.

Return ONLY valid JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if "```json" in result_text:
                result_text = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            elif "```" in result_text:
                result_text = re.search(r'```\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
            
            data = json.loads(result_text)
            
            # Create timeline
            timeline = ExperienceTimeline(
                total_years_claimed=float(data.get("total_claimed", 0)),
                total_years_validated=float(data.get("total_validated", 0)),
                red_flags=data.get("red_flags", [])
            )
            
            # Build experience breakdown
            breakdown = {}
            for job in data.get("jobs", []):
                job_type = job.get("type", "unclear")
                duration = float(job.get("duration_years", 0))
                
                if job_type == "project_delivery":
                    breakdown["Project Delivery"] = breakdown.get("Project Delivery", 0) + duration
                elif job_type == "support":
                    breakdown["Support/Maintenance"] = breakdown.get("Support/Maintenance", 0) + duration
                else:
                    breakdown["Unvalidated"] = breakdown.get("Unvalidated", 0) + duration
            
            timeline.experience_breakdown = breakdown
            
            # Generate red flags
            if timeline.total_years_claimed > 0:
                ratio = timeline.total_years_validated / timeline.total_years_claimed
                if ratio < 0.4:
                    timeline.red_flags.append(
                        f"⚠️ CRITICAL: Only {ratio:.0%} of claimed experience "
                        f"({timeline.total_years_validated:.1f}/{timeline.total_years_claimed:.1f} years) "
                        f"is validated project delivery work. Possible resume padding."
                    )
            
            return timeline
            
        except Exception as e:
            print(f"LLM timeline error: {e}")
            # Fallback
            return ExperienceTimeline(
                total_years_claimed=0.0,
                total_years_validated=0.0,
                red_flags=[f"Could not analyze timeline: {str(e)}"]
            )


class LLMPoweredResumeValidator:
    """Main validator using LLM for all analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required for LLM-powered validation")
        
        self.jd_analyzer = LLMPoweredJDAnalyzer(api_key)
        self.skill_validator = LLMPoweredSkillValidator(api_key)
        self.timeline_analyzer = LLMPoweredTimelineAnalyzer(api_key)
    
    def validate_candidate(
        self,
        jd_text: str,
        resume_text: str,
        candidate_name: str = "Candidate"
    ) -> CandidateValidationReport:
        """Complete validation using LLM intelligence"""
        
        print(f"🤖 Using LLM-powered validation for {candidate_name}...")
        
        # Step 1: Analyze JD with LLM
        print("   1/4 Analyzing JD...")
        jd_summary = self.jd_analyzer.analyze_jd(jd_text)
        
        # Step 2: Validate skills with LLM
        print(f"   2/4 Validating {len(jd_summary.mandatory_skills)} mandatory skills...")
        all_validations = []
        
        # Validate mandatory skills (limit to avoid too many API calls)
        for skill in jd_summary.mandatory_skills[:10]:  # Top 10 mandatory
            validation = self.skill_validator.validate_skill(skill.name, resume_text)
            all_validations.append((skill, validation))
        
        # Validate highly desired (top 5)
        for skill in jd_summary.highly_desired_skills[:5]:
            validation = self.skill_validator.validate_skill(skill.name, resume_text)
            all_validations.append((skill, validation))
        
        # Step 3: Categorize validations
        print("   3/4 Analyzing results...")
        validated_skills = []
        weak_skills = []
        missing_mandatory = []
        
        for jd_skill, validation in all_validations:
            if validation.validation_score >= 0.6:
                validated_skills.append(validation)
            elif validation.validation_score >= 0.2:
                weak_skills.append(validation)
            elif jd_skill.priority == SkillPriority.MANDATORY:
                missing_mandatory.append(jd_skill)
        
        # Step 4: Timeline analysis with LLM
        print("   4/4 Analyzing timeline...")
        timeline = self.timeline_analyzer.analyze_timeline(resume_text)
        
        # Calculate fit score
        fit_score = self._calculate_fit_score(
            jd_summary, validated_skills, weak_skills, missing_mandatory, timeline
        )
        
        # Generate report
        report = CandidateValidationReport(
            candidate_name=candidate_name,
            overall_fit_score=fit_score,
            jd_summary=jd_summary,
            validated_skills=validated_skills,
            weak_skills=weak_skills,
            missing_mandatory_skills=missing_mandatory,
            experience_timeline=timeline,
            real_project_count=len([v for v in validated_skills if v.experience_type == ExperienceType.REAL_PROJECT]),
            claimed_only_count=len([v for v in validated_skills if v.experience_type == ExperienceType.CLAIMED_KNOWLEDGE])
        )
        
        # Generate recommendations
        report.hiring_recommendation = self._generate_recommendation(report)
        report.interview_focus_areas = self._generate_interview_focus(report)
        report.critical_gaps = self._identify_critical_gaps(report)
        
        # Generate markdown
        report.detailed_markdown = self._generate_markdown(report)
        
        print(f"✅ Validation complete: {fit_score:.0f}/100")
        
        return report
    
    def _calculate_fit_score(self, jd_summary, validated, weak, missing, timeline) -> float:
        """Calculate fit score"""
        total_mandatory = len(jd_summary.mandatory_skills)
        if total_mandatory == 0:
            return 50.0
        
        mandatory_validated = len([
            v for v in validated
            if any(s.name.lower() == v.skill_name.lower() for s in jd_summary.mandatory_skills)
        ])
        
        mandatory_score = (mandatory_validated / total_mandatory) * 60
        
        avg_validation = sum(v.validation_score for v in validated) / len(validated) if validated else 0
        evidence_score = avg_validation * 25
        
        timeline_score = 0
        if timeline and timeline.total_years_claimed > 0:
            ratio = timeline.total_years_validated / timeline.total_years_claimed
            timeline_score = ratio * 15
        
        total = mandatory_score + evidence_score + timeline_score
        penalty = len(timeline.red_flags) if timeline else 0
        penalty *= 5
        
        return max(0, min(100, total - penalty))
    
    def _generate_recommendation(self, report) -> str:
        """Generate hiring recommendation"""
        if report.overall_fit_score >= 75:
            return "✅ STRONG FIT - Proceed to interview"
        elif report.overall_fit_score >= 60:
            return "⚠️ CONDITIONAL FIT - Interview with targeted questions"
        elif report.overall_fit_score >= 40:
            return "🟡 WEAK FIT - Consider if limited pool"
        else:
            return "❌ NOT RECOMMENDED - Significant gaps"
    
    def _generate_interview_focus(self, report) -> List[str]:
        """Generate interview focus areas"""
        focus = []
        for skill_val in report.weak_skills[:3]:
            focus.append(f"Validate {skill_val.skill_name}: {skill_val.gap_analysis}")
        return focus
    
    def _identify_critical_gaps(self, report) -> List[str]:
        """Identify critical gaps"""
        gaps = []
        for skill in report.missing_mandatory_skills:
            gaps.append(f"❌ Missing: {skill.name}")
        for flag in report.experience_timeline.red_flags if report.experience_timeline else []:
            gaps.append(flag)
        return gaps
    
    def _generate_markdown(self, report) -> str:
        """Generate markdown report"""
        md = f"""# Candidate Validation Report: {report.candidate_name}
## Overall Assessment
**Fit Score**: {report.overall_fit_score:.0f}/100
**Recommendation**: {report.hiring_recommendation}

---

## Skills Analysis
**Real Project Work**: {report.real_project_count} skills
**Claimed Only**: {report.claimed_only_count} skills
**Missing Mandatory**: {len(report.missing_mandatory_skills)} skills

"""
        
        if report.experience_timeline:
            t = report.experience_timeline
            ratio = (t.total_years_validated / t.total_years_claimed * 100) if t.total_years_claimed > 0 else 0
            md += f"""## Timeline Analysis
**Total Claimed**: {t.total_years_claimed:.1f} years
**Validated**: {t.total_years_validated:.1f} years
**Ratio**: {ratio:.0f}%

"""
        
        return md


# Export for use in main app
__all__ = [
    'LLMPoweredJDAnalyzer',
    'LLMPoweredSkillValidator',
    'LLMPoweredTimelineAnalyzer',
    'LLMPoweredResumeValidator'
]
