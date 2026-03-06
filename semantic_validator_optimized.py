"""
Enhanced Semantic Resume Validator with Deep Experience Analysis
================================================================

This module provides:
1. JD Summarization with keyword extraction
2. Semantic validation of real project experience vs. claimed knowledge
3. Experience timeline validation (claimed vs. actual)
4. Detailed gap analysis with improvement recommendations
5. Evidence-based scoring for each skill claim

Author: Optimized for deep candidate validation
Version: 3.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================
class ExperienceType(Enum):
    """Type of experience evidence found"""
    REAL_PROJECT = "Real Project Work"  # Actual project delivery with outcomes
    CLAIMED_KNOWLEDGE = "Claimed Knowledge"  # Listed skill without project evidence
    THEORETICAL = "Theoretical/Academic"  # Course/certification only
    UNVALIDATED = "Unvalidated Claim"  # No supporting evidence


class SkillPriority(Enum):
    """Priority level of skill from JD"""
    MANDATORY = "Mandatory (Must-Have)"
    HIGHLY_DESIRED = "Highly Desired"
    GOOD_TO_HAVE = "Good-to-Have"
    EXCLUDED = "Excluded (Red Flag)"


# ==================== DATA CLASSES ====================
@dataclass
class JDSkill:
    """Skill extracted from JD with context"""
    name: str
    priority: SkillPriority
    keywords: List[str] = field(default_factory=list)
    context: str = ""  # Where it appeared in JD


@dataclass
class JDSummary:
    """Structured summary of Job Description"""
    role_title: str
    role_archetype: str  # e.g., "Product Manager", "Engineer", etc.
    core_problem: str  # What problem is this role solving?
    
    mandatory_skills: List[JDSkill] = field(default_factory=list)
    highly_desired_skills: List[JDSkill] = field(default_factory=list)
    good_to_have_skills: List[JDSkill] = field(default_factory=list)
    excluded_skills: List[JDSkill] = field(default_factory=list)
    
    required_experience_years: Optional[int] = None
    domain_requirements: List[str] = field(default_factory=list)
    
    search_keywords: List[str] = field(default_factory=list)
    reject_keywords: List[str] = field(default_factory=list)


@dataclass
class ProjectEvidence:
    """Evidence of real project work"""
    project_name: str
    role_in_project: str
    technologies_used: List[str]
    outcomes: List[str]  # Quantified business impact
    duration: Optional[str] = None
    evidence_strength: float = 0.0  # 0-1 score
    evidence_type: ExperienceType = ExperienceType.UNVALIDATED


@dataclass
class SkillValidation:
    """Validation result for a single skill"""
    skill_name: str
    claimed_in_resume: bool = False
    experience_type: ExperienceType = ExperienceType.UNVALIDATED
    evidence: List[ProjectEvidence] = field(default_factory=list)
    validation_score: float = 0.0  # 0-1
    gap_analysis: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class ExperienceTimeline:
    """Timeline validation for experience claims"""
    total_years_claimed: float
    total_years_validated: float
    timeline_gaps: List[str] = field(default_factory=list)
    experience_breakdown: Dict[str, float] = field(default_factory=dict)
    red_flags: List[str] = field(default_factory=list)


@dataclass
class CandidateValidationReport:
    """Complete validation report for candidate"""
    candidate_name: str
    overall_fit_score: float  # 0-100
    
    jd_summary: JDSummary
    
    # Skill validations
    validated_skills: List[SkillValidation] = field(default_factory=list)
    weak_skills: List[SkillValidation] = field(default_factory=list)
    missing_mandatory_skills: List[JDSkill] = field(default_factory=list)
    
    # Experience analysis
    experience_timeline: Optional[ExperienceTimeline] = None
    
    # Gap analysis
    critical_gaps: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    
    # Recommendations
    hiring_recommendation: str = ""
    interview_focus_areas: List[str] = field(default_factory=list)
    
    # Evidence summary
    real_project_count: int = 0
    claimed_only_count: int = 0
    
    detailed_markdown: str = ""


# ==================== JD ANALYZER ====================
class EnhancedJDAnalyzer:
    """Parse and summarize Job Descriptions with skill extraction"""
    
    def analyze_jd(self, jd_text: str) -> JDSummary:
        """Comprehensive JD analysis"""
        summary = JDSummary(
            role_title=self._extract_role_title(jd_text),
            role_archetype=self._extract_role_archetype(jd_text),
            core_problem=self._extract_core_problem(jd_text)
        )
        
        # Extract skills by priority
        summary.mandatory_skills = self._extract_mandatory_skills(jd_text)
        summary.highly_desired_skills = self._extract_highly_desired_skills(jd_text)
        summary.good_to_have_skills = self._extract_good_to_have_skills(jd_text)
        summary.excluded_skills = self._extract_excluded_skills(jd_text)
        
        # Extract other requirements
        summary.required_experience_years = self._extract_experience_requirement(jd_text)
        summary.domain_requirements = self._extract_domain_requirements(jd_text)
        
        # Generate search keywords
        summary.search_keywords = self._generate_search_keywords(summary)
        summary.reject_keywords = self._generate_reject_keywords(summary)
        
        return summary
    
    def _extract_role_title(self, jd_text: str) -> str:
        """Extract role title from JD"""
        # Look for common patterns
        patterns = [
            r"(?:role|position|title):\s*([^\n]+)",
            r"hiring\s+(?:for\s+)?(?:a\s+)?([A-Z][^\n]+?)(?:\s+who|\s+to)",
            r"^([A-Z][A-Za-z\s&/]+(?:Manager|Lead|Engineer|Analyst|Consultant))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, jd_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return "Position Not Specified"
    
    def _extract_role_archetype(self, jd_text: str) -> str:
        """Identify role archetype"""
        jd_lower = jd_text.lower()
        
        archetypes = {
            'Product Manager': ['product manager', 'product lead', 'product owner', 'pm role'],
            'Program Manager': ['program manager', 'delivery lead', 'implementation lead', 'transformation lead'],
            'Software Engineer': ['software engineer', 'developer', 'backend', 'frontend'],
            'Data Scientist': ['data scientist', 'ml engineer', 'machine learning'],
            'Business Analyst': ['business analyst', 'ba role', 'requirements analyst'],
            'Consultant': ['consultant', 'solution consultant', 'advisory'],
        }
        
        for archetype, keywords in archetypes.items():
            if any(kw in jd_lower for kw in keywords):
                return archetype
        
        return "General"
    
    def _extract_core_problem(self, jd_text: str) -> str:
        """Extract the core problem this role solves"""
        patterns = [
            r"core problem[:\s]+([^\n]+(?:\n(?!\n)[^\n]+)*)",
            r"what success looks like[:\s]+([^\n]+(?:\n(?!\n)[^\n]+)*)",
            r"(?:we are|we're)\s+(?:hiring|looking)\s+for[:\s]+([^\n]+(?:\n(?!\n)[^\n]+)*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, jd_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()[:300]  # Limit length
        
        return "Not explicitly stated in JD"
    
    def _extract_mandatory_skills(self, jd_text: str) -> List[JDSkill]:
        """Extract must-have/mandatory skills"""
        skills = []
        
        # Section patterns for mandatory skills
        patterns = [
            r"must[- ]have[:\s]+(.*?)(?:\n\n|good[- ]to[- ]have|nice[- ]to[- ]have|$)",
            r"required[:\s]+(.*?)(?:\n\n|preferred|desired|$)",
            r"mandatory[:\s]+(.*?)(?:\n\n|optional|$)",
            r"non[- ]negotiable[:\s]+(.*?)(?:\n\n|flexible|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, jd_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted_skills = self._parse_skill_list(match)
                for skill_name in extracted_skills:
                    skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.MANDATORY,
                        keywords=self._generate_skill_keywords(skill_name),
                        context="Mandatory/Must-Have section"
                    ))
        
        return self._deduplicate_skills(skills)
    
    def _extract_highly_desired_skills(self, jd_text: str) -> List[JDSkill]:
        """Extract highly desired/preferred skills"""
        skills = []
        
        patterns = [
            r"highly\s+desired[:\s]+(.*?)(?:\n\n|good[- ]to[- ]have|$)",
            r"preferred[:\s]+(.*?)(?:\n\n|nice[- ]to[- ]have|$)",
            r"strong\s+signals?[:\s]+(.*?)(?:\n\n|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, jd_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted_skills = self._parse_skill_list(match)
                for skill_name in extracted_skills:
                    skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.HIGHLY_DESIRED,
                        keywords=self._generate_skill_keywords(skill_name),
                        context="Highly Desired/Preferred section"
                    ))
        
        return self._deduplicate_skills(skills)
    
    def _extract_good_to_have_skills(self, jd_text: str) -> List[JDSkill]:
        """Extract good-to-have/nice-to-have skills"""
        skills = []
        
        patterns = [
            r"good[- ]to[- ]have[:\s]+(.*?)(?:\n\n|what we do not|$)",
            r"nice[- ]to[- ]have[:\s]+(.*?)(?:\n\n|not required|$)",
            r"bonus[:\s]+(.*?)(?:\n\n|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, jd_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted_skills = self._parse_skill_list(match)
                for skill_name in extracted_skills:
                    skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.GOOD_TO_HAVE,
                        keywords=self._generate_skill_keywords(skill_name),
                        context="Good-to-Have/Nice-to-Have section"
                    ))
        
        return self._deduplicate_skills(skills)
    
    def _extract_excluded_skills(self, jd_text: str) -> List[JDSkill]:
        """Extract skills to exclude/red flags"""
        skills = []
        
        patterns = [
            r"not\s+(?:looking|hiring)\s+for[:\s]+(.*?)(?:\n\n|$)",
            r"do\s+not\s+need[:\s]+(.*?)(?:\n\n|$)",
            r"avoid[:\s]+(.*?)(?:\n\n|$)",
            r"(?:reject|deprioritize)\s+keywords?[:\s]+(.*?)(?:\n\n|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, jd_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted_skills = self._parse_skill_list(match)
                for skill_name in extracted_skills:
                    skills.append(JDSkill(
                        name=skill_name,
                        priority=SkillPriority.EXCLUDED,
                        keywords=self._generate_skill_keywords(skill_name),
                        context="Excluded/Not Looking For section"
                    ))
        
        return self._deduplicate_skills(skills)
    
    def _extract_experience_requirement(self, jd_text: str) -> Optional[int]:
        """Extract required years of experience"""
        patterns = [
            r"(\d+)[-–+]?\s*(?:to\s+\d+\s*)?years?\s+(?:of\s+)?experience",
            r"experience[:\s]+(\d+)[-–+]?\s*years?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, jd_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_domain_requirements(self, jd_text: str) -> List[str]:
        """Extract domain/industry requirements"""
        domains = []
        
        domain_keywords = {
            'life sciences', 'pharma', 'healthcare', 'medtech', 'biotech',
            'clinical', 'regulatory', 'compliance', 'pharmacovigilance',
            'medical writing', 'medical affairs'
        }
        
        jd_lower = jd_text.lower()
        for domain in domain_keywords:
            if domain in jd_lower:
                domains.append(domain.title())
        
        return list(set(domains))
    
    def _parse_skill_list(self, text: str) -> List[str]:
        """Parse a list of skills from text"""
        skills = []
        
        # Split by common delimiters
        items = re.split(r'[,\n•\-\*●○▪▫]', text)
        
        for item in items:
            # Clean up
            skill = item.strip()
            skill = re.sub(r'\(.*?\)', '', skill)  # Remove parentheses
            skill = re.sub(r'\d+\+?\s*years?', '', skill, flags=re.IGNORECASE)
            skill = skill.strip()
            
            # Filter valid skills
            if skill and 2 < len(skill) < 100 and not re.match(r'^\d+$', skill):
                skills.append(skill)
        
        return skills
    
    def _generate_skill_keywords(self, skill_name: str) -> List[str]:
        """Generate semantic keywords for skill matching"""
        keywords = [skill_name.lower()]
        
        # Add common variations
        skill_lower = skill_name.lower()
        
        # Abbreviations
        if 'genai' in skill_lower or 'generative ai' in skill_lower:
            keywords.extend(['genai', 'generative ai', 'gen ai', 'llm'])
        
        if 'rag' in skill_lower:
            keywords.extend(['rag', 'retrieval augmented generation', 'retrieval-augmented'])
        
        if 'prompt engineering' in skill_lower:
            keywords.extend(['prompting', 'prompt design', 'prompt optimization'])
        
        if 'product manager' in skill_lower or 'pm' in skill_lower:
            keywords.extend(['product management', 'product lead', 'product owner'])
        
        # Add more domain-specific mappings as needed
        
        return list(set(keywords))
    
    def _deduplicate_skills(self, skills: List[JDSkill]) -> List[JDSkill]:
        """Remove duplicate skills"""
        seen = set()
        unique = []
        
        for skill in skills:
            skill_lower = skill.name.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique.append(skill)
        
        return unique
    
    def _generate_search_keywords(self, summary: JDSummary) -> List[str]:
        """Generate keywords for candidate search"""
        keywords = []
        
        # From mandatory skills
        for skill in summary.mandatory_skills:
            keywords.extend(skill.keywords)
        
        # From role archetype
        keywords.append(summary.role_archetype.lower())
        
        # From domains
        keywords.extend([d.lower() for d in summary.domain_requirements])
        
        return list(set(keywords))[:20]  # Limit to top 20
    
    def _generate_reject_keywords(self, summary: JDSummary) -> List[str]:
        """Generate keywords to reject candidates"""
        keywords = []
        
        for skill in summary.excluded_skills:
            keywords.extend(skill.keywords)
        
        return list(set(keywords))


# ==================== SEMANTIC EXPERIENCE VALIDATOR ====================
class SemanticExperienceValidator:
    """Validate real project experience vs. claimed knowledge"""
    
    def __init__(self):
        # Patterns indicating real project work
        self.project_indicators = {
            'strong': [
                r'designed\s+(?:and\s+)?(?:implemented|developed|built|created)',
                r'led\s+(?:the\s+)?(?:development|implementation|design)',
                r'delivered\s+(?:a\s+)?(?:solution|product|system|platform)',
                r'shipped\s+(?:a\s+)?(?:feature|product|solution)',
                r'reduced\s+.*?\s+(?:from|by)\s+\d+',
                r'increased\s+.*?\s+(?:from|by)\s+\d+',
                r'achieved\s+\d+%',
            ],
            'moderate': [
                r'worked\s+on\s+(?:a\s+)?project',
                r'participated\s+in',
                r'contributed\s+to',
                r'assisted\s+with',
            ],
            'weak': [
                r'familiar\s+with',
                r'knowledge\s+of',
                r'exposure\s+to',
                r'basic\s+understanding',
            ]
        }
        
        # Outcome indicators (quantified results)
        self.outcome_patterns = [
            r'(\d+%)\s+(?:increase|improvement|growth|reduction|decrease)',
            r'reduced\s+.*?\s+from\s+(.*?)\s+to\s+(.*?)(?:\s|,|\.)',
            r'(\d+[xX])\s+faster',
            r'saved\s+(\$?\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:million|thousand|k|m))?)',
        ]
    
    def validate_skill_experience(
        self,
        skill_name: str,
        resume_text: str
    ) -> SkillValidation:
        """Validate if skill has real project evidence"""
        
        validation = SkillValidation(skill_name=skill_name, claimed_in_resume=False)
        
        # Check if skill is mentioned
        skill_lower = skill_name.lower()
        resume_lower = resume_text.lower()
        
        if skill_lower not in resume_lower:
            validation.experience_type = ExperienceType.UNVALIDATED
            validation.validation_score = 0.0
            validation.gap_analysis = f"Skill '{skill_name}' not found in resume"
            return validation
        
        validation.claimed_in_resume = True
        
        # Extract project evidence
        validation.evidence = self._extract_project_evidence(skill_name, resume_text)
        
        # Determine experience type and score
        if validation.evidence:
            # Check quality of evidence
            has_strong_indicators = any(
                e.evidence_strength > 0.7 for e in validation.evidence
            )
            has_outcomes = any(e.outcomes for e in validation.evidence)
            
            if has_strong_indicators and has_outcomes:
                validation.experience_type = ExperienceType.REAL_PROJECT
                validation.validation_score = 0.8 + (len(validation.evidence) * 0.05)
            elif has_strong_indicators or has_outcomes:
                validation.experience_type = ExperienceType.REAL_PROJECT
                validation.validation_score = 0.6
            else:
                validation.experience_type = ExperienceType.CLAIMED_KNOWLEDGE
                validation.validation_score = 0.4
        else:
            # Skill mentioned but no project evidence
            validation.experience_type = ExperienceType.CLAIMED_KNOWLEDGE
            validation.validation_score = 0.2
        
        # Generate gap analysis
        validation.gap_analysis = self._generate_gap_analysis(validation)
        validation.improvement_suggestions = self._generate_improvement_suggestions(validation)
        
        return validation
    
    def _extract_project_evidence(
        self,
        skill_name: str,
        resume_text: str
    ) -> List[ProjectEvidence]:
        """Extract actual project work evidence for a skill"""
        evidence_list = []
        
        # Find sections mentioning the skill
        skill_contexts = self._find_skill_contexts(skill_name, resume_text)
        
        for context in skill_contexts:
            # Extract project details
            project = self._parse_project_from_context(context, skill_name)
            if project:
                evidence_list.append(project)
        
        return evidence_list
    
    def _find_skill_contexts(self, skill_name: str, resume_text: str, window=500) -> List[str]:
        """Find text contexts where skill is mentioned"""
        contexts = []
        skill_lower = skill_name.lower()
        resume_lower = resume_text.lower()
        
        # Find all occurrences
        start = 0
        while True:
            pos = resume_lower.find(skill_lower, start)
            if pos == -1:
                break
            
            # Extract context window
            context_start = max(0, pos - window)
            context_end = min(len(resume_text), pos + window)
            context = resume_text[context_start:context_end]
            
            contexts.append(context)
            start = pos + 1
        
        return contexts
    
    def _parse_project_from_context(self, context: str, skill_name: str) -> Optional[ProjectEvidence]:
        """Parse project evidence from context"""
        project = ProjectEvidence(
            project_name="Unnamed Project",
            role_in_project="Not specified",
            technologies_used=[skill_name],
            outcomes=[]
        )
        
        # Calculate evidence strength
        strength = 0.0
        
        # Check for strong indicators
        for pattern in self.project_indicators['strong']:
            if re.search(pattern, context, re.IGNORECASE):
                strength += 0.3
        
        # Check for moderate indicators
        for pattern in self.project_indicators['moderate']:
            if re.search(pattern, context, re.IGNORECASE):
                strength += 0.15
        
        # Extract outcomes
        for pattern in self.outcome_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            if matches:
                project.outcomes.extend([str(m) for m in matches])
                strength += 0.2
        
        project.evidence_strength = min(1.0, strength)
        
        # Determine experience type
        if strength > 0.5:
            project.evidence_type = ExperienceType.REAL_PROJECT
        elif strength > 0.2:
            project.evidence_type = ExperienceType.CLAIMED_KNOWLEDGE
        else:
            project.evidence_type = ExperienceType.THEORETICAL
        
        # Only return if there's some evidence
        return project if strength > 0 else None
    
    def _generate_gap_analysis(self, validation: SkillValidation) -> str:
        """Generate gap analysis for skill"""
        if validation.experience_type == ExperienceType.REAL_PROJECT:
            if validation.validation_score >= 0.8:
                return f"✅ VALIDATED: Strong evidence of real project work with {validation.skill_name}"
            else:
                return f"⚠️ PARTIAL: Some project evidence, but lacks detailed outcomes or depth"
        
        elif validation.experience_type == ExperienceType.CLAIMED_KNOWLEDGE:
            return f"❌ NOT VALIDATED: {validation.skill_name} mentioned but no concrete project evidence found"
        
        else:
            return f"❌ MISSING: No evidence of {validation.skill_name} in resume"
    
    def _generate_improvement_suggestions(self, validation: SkillValidation) -> List[str]:
        """Generate suggestions for improvement"""
        suggestions = []
        
        if validation.experience_type == ExperienceType.CLAIMED_KNOWLEDGE:
            suggestions.append(
                f"Interview Question: 'Walk me through a specific project where you used {validation.skill_name}. "
                f"What was the problem, your approach, and the measurable outcome?'"
            )
            suggestions.append(
                f"Ask for concrete examples: timelines, team size, your specific role, deliverables"
            )
        
        elif validation.experience_type == ExperienceType.REAL_PROJECT:
            if validation.validation_score < 0.8:
                suggestions.append(
                    f"Probe deeper on technical implementation: 'How did you handle [specific challenge] "
                    f"when implementing {validation.skill_name}?'"
                )
        
        else:
            suggestions.append(
                f"Critical Gap: Candidate claims overall experience but has no evidence of {validation.skill_name}. "
                f"This may be a resume padding issue."
            )
        
        return suggestions


# ==================== EXPERIENCE TIMELINE VALIDATOR ====================
class ExperienceTimelineValidator:
    """Validate claimed experience vs. actual project timelines"""
    
    def validate_timeline(self, resume_text: str) -> ExperienceTimeline:
        """Analyze experience timeline for gaps and inconsistencies"""
        timeline = ExperienceTimeline(
            total_years_claimed=0.0,
            total_years_validated=0.0,
            experience_breakdown={}
        )
        
        # Extract employment history
        jobs = self._extract_employment_history(resume_text)
        
        # Calculate total claimed years
        for job in jobs:
            duration = job.get('duration_years', 0)
            timeline.total_years_claimed += duration
            
            # Categorize by type of work
            if self._is_project_delivery_work(job):
                timeline.experience_breakdown['Project Delivery'] = \
                    timeline.experience_breakdown.get('Project Delivery', 0) + duration
                timeline.total_years_validated += duration
            elif self._is_support_work(job):
                timeline.experience_breakdown['Support/Maintenance'] = \
                    timeline.experience_breakdown.get('Support/Maintenance', 0) + duration
            else:
                timeline.experience_breakdown['Unvalidated'] = \
                    timeline.experience_breakdown.get('Unvalidated', 0) + duration
        
        # Detect red flags
        timeline.red_flags = self._detect_timeline_red_flags(jobs, timeline)
        
        # Identify gaps
        timeline.timeline_gaps = self._identify_gaps(jobs)
        
        return timeline
    
    def _extract_employment_history(self, resume_text: str) -> List[Dict]:
        """Extract employment history from resume"""
        jobs = []
        
        # Pattern for job entries
        job_pattern = r'(?:^|\n)([A-Z][^|\n]+?)\s*\|\s*([A-Z][^|\n]+?)\s*(?:\||$)'
        date_pattern = r'(\d{1,2}/\d{4}|\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|\d{4}|present|current)'
        
        lines = resume_text.split('\n')
        current_job = None
        
        for i, line in enumerate(lines):
            # Look for job title pattern
            job_match = re.search(job_pattern, line, re.IGNORECASE)
            if job_match:
                # Look for dates in surrounding lines
                search_window = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                date_match = re.search(date_pattern, search_window, re.IGNORECASE)
                
                if date_match:
                    start_date = date_match.group(1)
                    end_date = date_match.group(2)
                    
                    duration = self._calculate_duration(start_date, end_date)
                    
                    current_job = {
                        'title': job_match.group(1).strip(),
                        'company': job_match.group(2).strip(),
                        'start_date': start_date,
                        'end_date': end_date,
                        'duration_years': duration,
                        'description': ''
                    }
                    jobs.append(current_job)
        
        return jobs
    
    def _calculate_duration(self, start_str: str, end_str: str) -> float:
        """Calculate duration in years between dates"""
        try:
            # Simple year extraction
            start_year = int(re.search(r'\d{4}', start_str).group())
            
            if 'present' in end_str.lower() or 'current' in end_str.lower():
                end_year = datetime.now().year
            else:
                end_year = int(re.search(r'\d{4}', end_str).group())
            
            return max(0, end_year - start_year)
        except:
            return 0.0
    
    def _is_project_delivery_work(self, job: Dict) -> bool:
        """Check if job involves project delivery"""
        indicators = ['led', 'delivered', 'shipped', 'implemented', 'designed', 'built']
        description = job.get('description', '').lower() + job.get('title', '').lower()
        
        return any(indicator in description for indicator in indicators)
    
    def _is_support_work(self, job: Dict) -> bool:
        """Check if job is support/maintenance work"""
        indicators = ['support', 'maintenance', 'operations', 'helpdesk', 'admin']
        description = job.get('description', '').lower() + job.get('title', '').lower()
        
        return any(indicator in description for indicator in indicators)
    
    def _detect_timeline_red_flags(self, jobs: List[Dict], timeline: ExperienceTimeline) -> List[str]:
        """Detect suspicious patterns in timeline"""
        red_flags = []
        
        # Flag 1: Claimed years >> Validated years
        if timeline.total_years_claimed > 0:
            validation_ratio = timeline.total_years_validated / timeline.total_years_claimed
            
            if validation_ratio < 0.3:
                red_flags.append(
                    f"⚠️ CRITICAL: Only {validation_ratio:.0%} of claimed experience "
                    f"({timeline.total_years_validated:.1f}/{timeline.total_years_claimed:.1f} years) "
                    f"is validated project delivery work. May be padding overall experience."
                )
        
        # Flag 2: Too many short stints
        short_jobs = [j for j in jobs if j.get('duration_years', 0) < 1]
        if len(short_jobs) > 3:
            red_flags.append(
                f"⚠️ Job hopping: {len(short_jobs)} positions with <1 year tenure"
            )
        
        return red_flags
    
    def _identify_gaps(self, jobs: List[Dict]) -> List[str]:
        """Identify gaps in employment"""
        # Simplified - could be enhanced with actual gap detection
        gaps = []
        
        # Sort jobs by start date
        # ... implementation details ...
        
        return gaps


# ==================== MAIN VALIDATOR ====================
class EnhancedResumeValidator:
    """Main validator orchestrating all validation logic"""
    
    def __init__(self):
        self.jd_analyzer = EnhancedJDAnalyzer()
        self.experience_validator = SemanticExperienceValidator()
        self.timeline_validator = ExperienceTimelineValidator()
    
    def validate_candidate(
        self,
        jd_text: str,
        resume_text: str,
        candidate_name: str = "Candidate"
    ) -> CandidateValidationReport:
        """Complete validation of candidate against JD"""
        
        # Step 1: Analyze JD
        jd_summary = self.jd_analyzer.analyze_jd(jd_text)
        
        # Step 2: Validate each skill
        all_validations = []
        
        # Validate mandatory skills
        for skill in jd_summary.mandatory_skills:
            validation = self.experience_validator.validate_skill_experience(
                skill.name, resume_text
            )
            all_validations.append((skill, validation))
        
        # Validate highly desired skills
        for skill in jd_summary.highly_desired_skills:
            validation = self.experience_validator.validate_skill_experience(
                skill.name, resume_text
            )
            all_validations.append((skill, validation))
        
        # Step 3: Categorize validations
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
        
        # Step 4: Timeline validation
        timeline = self.timeline_validator.validate_timeline(resume_text)
        
        # Step 5: Calculate overall fit score
        fit_score = self._calculate_fit_score(
            jd_summary, validated_skills, weak_skills, missing_mandatory, timeline
        )
        
        # Step 6: Generate report
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
        
        # Step 7: Generate recommendations
        report.hiring_recommendation = self._generate_hiring_recommendation(report)
        report.interview_focus_areas = self._generate_interview_focus(report)
        report.critical_gaps = self._identify_critical_gaps(report)
        report.improvement_areas = self._identify_improvement_areas(report)
        
        # Step 8: Generate markdown report
        report.detailed_markdown = self._generate_detailed_markdown(report)
        
        return report
    
    def _calculate_fit_score(
        self,
        jd_summary: JDSummary,
        validated: List[SkillValidation],
        weak: List[SkillValidation],
        missing: List[JDSkill],
        timeline: ExperienceTimeline
    ) -> float:
        """Calculate overall fit score (0-100)"""
        
        total_mandatory = len(jd_summary.mandatory_skills)
        if total_mandatory == 0:
            return 50.0  # Default if no mandatory skills
        
        # Mandatory skills weight: 60%
        mandatory_validated = len([
            v for v in validated
            if any(s.name.lower() == v.skill_name.lower() for s in jd_summary.mandatory_skills)
        ])
        mandatory_score = (mandatory_validated / total_mandatory) * 60
        
        # Quality of evidence weight: 25%
        avg_validation_score = sum(v.validation_score for v in validated) / len(validated) if validated else 0
        evidence_score = avg_validation_score * 25
        
        # Timeline validation weight: 15%
        timeline_score = 0
        if timeline.total_years_claimed > 0:
            timeline_ratio = timeline.total_years_validated / timeline.total_years_claimed
            timeline_score = timeline_ratio * 15
        
        total = mandatory_score + evidence_score + timeline_score
        
        # Penalize for red flags
        penalty = len(timeline.red_flags) * 5
        
        return max(0, min(100, total - penalty))
    
    def _generate_hiring_recommendation(self, report: CandidateValidationReport) -> str:
        """Generate hiring recommendation"""
        if report.overall_fit_score >= 75:
            return "✅ STRONG FIT - Proceed to interview with focus on depth validation"
        elif report.overall_fit_score >= 60:
            return "⚠️ CONDITIONAL FIT - Interview with targeted questions on gaps"
        elif report.overall_fit_score >= 40:
            return "🟡 WEAK FIT - Consider only if talent pool is limited"
        else:
            return "❌ NOT RECOMMENDED - Significant gaps in mandatory requirements"
    
    def _generate_interview_focus(self, report: CandidateValidationReport) -> List[str]:
        """Generate interview focus areas"""
        focus_areas = []
        
        # Focus on weak skills
        for skill_val in report.weak_skills[:3]:
            focus_areas.append(
                f"Validate {skill_val.skill_name}: {skill_val.gap_analysis}"
            )
        
        # Focus on timeline gaps
        if report.experience_timeline and report.experience_timeline.red_flags:
            focus_areas.append(
                "Clarify experience timeline discrepancies"
            )
        
        return focus_areas
    
    def _identify_critical_gaps(self, report: CandidateValidationReport) -> List[str]:
        """Identify critical gaps"""
        gaps = []
        
        for skill in report.missing_mandatory_skills:
            gaps.append(f"❌ Missing mandatory skill: {skill.name}")
        
        for red_flag in (report.experience_timeline.red_flags if report.experience_timeline else []):
            gaps.append(red_flag)
        
        return gaps
    
    def _identify_improvement_areas(self, report: CandidateValidationReport) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        for skill_val in report.weak_skills:
            improvements.extend(skill_val.improvement_suggestions)
        
        return improvements[:5]  # Limit to top 5
    
    def _generate_detailed_markdown(self, report: CandidateValidationReport) -> str:
        """Generate detailed markdown report"""
        
        md = f"""# Candidate Validation Report: {report.candidate_name}

## Overall Assessment
**Fit Score**: {report.overall_fit_score:.0f}/100
**Recommendation**: {report.hiring_recommendation}

---

## JD Summary

**Role**: {report.jd_summary.role_title}
**Archetype**: {report.jd_summary.role_archetype}
**Core Problem**: {report.jd_summary.core_problem}

### Required Skills Breakdown
"""
        
        # Mandatory skills
        md += f"\n#### Mandatory Skills ({len(report.jd_summary.mandatory_skills)})\n"
        for skill in report.jd_summary.mandatory_skills[:10]:
            md += f"- {skill.name}\n"
        
        # Good to have
        if report.jd_summary.good_to_have_skills:
            md += f"\n#### Good-to-Have Skills ({len(report.jd_summary.good_to_have_skills)})\n"
            for skill in report.jd_summary.good_to_have_skills[:5]:
                md += f"- {skill.name}\n"
        
        # Excluded
        if report.jd_summary.excluded_skills:
            md += f"\n#### Excluded/Red Flag Skills ({len(report.jd_summary.excluded_skills)})\n"
            for skill in report.jd_summary.excluded_skills[:5]:
                md += f"- ⛔ {skill.name}\n"
        
        # Experience analysis
        md += "\n---\n\n## Experience Timeline Analysis\n\n"
        if report.experience_timeline:
            timeline = report.experience_timeline
            md += f"**Total Experience Claimed**: {timeline.total_years_claimed:.1f} years\n"
            md += f"**Validated Project Delivery**: {timeline.total_years_validated:.1f} years\n"
            
            if timeline.total_years_claimed > 0:
                ratio = timeline.total_years_validated / timeline.total_years_claimed
                md += f"**Validation Ratio**: {ratio:.0%}\n\n"
            
            if timeline.experience_breakdown:
                md += "**Experience Breakdown**:\n"
                for category, years in timeline.experience_breakdown.items():
                    md += f"- {category}: {years:.1f} years\n"
            
            if timeline.red_flags:
                md += "\n### ⚠️ Timeline Red Flags:\n"
                for flag in timeline.red_flags:
                    md += f"- {flag}\n"
        
        # Validated skills
        md += "\n---\n\n## Validated Skills\n\n"
        md += f"**Real Project Experience**: {report.real_project_count} skills\n"
        md += f"**Claimed Knowledge Only**: {report.claimed_only_count} skills\n\n"
        
        # Detail validated skills
        for skill_val in report.validated_skills:
            md += f"\n### ✅ {skill_val.skill_name}\n"
            md += f"**Experience Type**: {skill_val.experience_type.value}\n"
            md += f"**Validation Score**: {skill_val.validation_score:.0%}\n"
            md += f"**Analysis**: {skill_val.gap_analysis}\n"
            
            if skill_val.evidence:
                md += f"\n**Project Evidence** ({len(skill_val.evidence)} found):\n"
                for i, evidence in enumerate(skill_val.evidence[:2], 1):
                    md += f"{i}. Strength: {evidence.evidence_strength:.0%}"
                    if evidence.outcomes:
                        md += f" | Outcomes: {', '.join(evidence.outcomes[:2])}"
                    md += "\n"
        
        # Weak/missing skills
        if report.weak_skills:
            md += "\n---\n\n## ⚠️ Weak/Unvalidated Skills\n\n"
            for skill_val in report.weak_skills:
                md += f"\n### {skill_val.skill_name}\n"
                md += f"{skill_val.gap_analysis}\n"
                if skill_val.improvement_suggestions:
                    md += "**Interview Probes**:\n"
                    for suggestion in skill_val.improvement_suggestions:
                        md += f"- {suggestion}\n"
        
        # Missing mandatory
        if report.missing_mandatory_skills:
            md += "\n---\n\n## ❌ Critical Gaps (Missing Mandatory Skills)\n\n"
            for skill in report.missing_mandatory_skills:
                md += f"- {skill.name}\n"
        
        # Interview focus
        if report.interview_focus_areas:
            md += "\n---\n\n## Interview Focus Areas\n\n"
            for i, area in enumerate(report.interview_focus_areas, 1):
                md += f"{i}. {area}\n"
        
        md += "\n---\n\n*Report generated by Enhanced Semantic Validator v3.0*\n"
        
        return md


# ==================== EXPORT FUNCTIONS ====================
def generate_jd_summary_markdown(jd_summary: JDSummary) -> str:
    """Generate standalone JD summary"""
    
    md = f"""# Job Description Analysis

## Role Overview
**Title**: {jd_summary.role_title}
**Archetype**: {jd_summary.role_archetype}
**Core Problem**: {jd_summary.core_problem}

## Skills Requirements

### Mandatory (Must-Have)
"""
    
    for skill in jd_summary.mandatory_skills:
        md += f"- **{skill.name}**\n"
        if skill.keywords:
            md += f"  - Keywords: {', '.join(skill.keywords[:5])}\n"
    
    md += "\n### Highly Desired\n"
    for skill in jd_summary.highly_desired_skills:
        md += f"- **{skill.name}**\n"
    
    md += "\n### Good-to-Have\n"
    for skill in jd_summary.good_to_have_skills:
        md += f"- {skill.name}\n"
    
    if jd_summary.excluded_skills:
        md += "\n### ⛔ Excluded/Red Flags\n"
        for skill in jd_summary.excluded_skills:
            md += f"- {skill.name}\n"
    
    md += "\n## Search Keywords\n"
    md += "Target: " + ", ".join(jd_summary.search_keywords) + "\n"
    
    if jd_summary.reject_keywords:
        md += "\nReject: " + ", ".join(jd_summary.reject_keywords) + "\n"
    
    return md


# ==================== USAGE EXAMPLE ====================
if __name__ == "__main__":
    # Example usage
    validator = EnhancedResumeValidator()
    
    jd_text = """
    Role: GenAI Product Manager
    
    Must-have:
    - GenAI implementation experience
    - Product management in regulated domains
    - Stakeholder management
    
    Not looking for:
    - ML researchers
    - Model trainers
    """
    
    resume_text = """
    Senior Product Manager | Pharma Co | 2020-2024
    
    Led GenAI chatbot implementation reducing response time by 80%.
    Managed cross-functional stakeholders.
    """
    
    report = validator.validate_candidate(jd_text, resume_text, "John Doe")
    
    print(report.detailed_markdown)
