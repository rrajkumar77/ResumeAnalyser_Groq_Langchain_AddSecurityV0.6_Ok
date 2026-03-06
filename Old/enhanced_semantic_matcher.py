"""
Enhanced Semantic Skill Matcher with Hands-On Experience Validation
=====================================================================
Improvements over base semantic_skill_matcher.py:
1. Distinguishes hands-on project experience from passive mentions
2. Validates actual usage vs. resume padding (skills-only listings)
3. Provides experience depth scoring (shallow mention vs. deep expertise)
4. User-configurable priority skills for targeted evaluation
5. Enhanced action verb detection with experience intensity scoring

Core Enhancement:
- Validates whether candidates have *actually worked* with technology
- Scores evidence based on project outcomes, metrics, and hands-on indicators
- Filters out superficial skill mentions without substantive context
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import numpy as np
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

# Import base classes (extend existing implementation)
from semantic_skill_matcher import (
    SkillValidationStatus,
    ContextType,
    SkillEvidence,
    SkillValidationResult,
    SkillMatchingReport,
    ResumeSectionExtractor,
    SemanticEmbeddingMatcher,
)

# Import skill filter to remove false positives
from skill_filter import SkillFilter


class ExperienceDepth(Enum):
    """Classification of experience depth for a skill."""
    EXPERT = "EXPERT"  # Deep hands-on experience with measurable outcomes
    PROFICIENT = "PROFICIENT"  # Substantial project work with clear responsibilities
    COMPETENT = "COMPETENT"  # Moderate hands-on experience
    BASIC = "BASIC"  # Limited or shallow exposure
    MENTIONED_ONLY = "MENTIONED_ONLY"  # Listed but no evidence of use
    NOT_FOUND = "NOT_FOUND"  # Not mentioned in resume


class ActionVerbIntensity(Enum):
    """Intensity levels for action verbs indicating hands-on depth."""
    LEADERSHIP = "LEADERSHIP"  # Led, architected, designed, owned
    CORE_DELIVERY = "CORE_DELIVERY"  # Built, implemented, developed, created
    CONTRIBUTION = "CONTRIBUTION"  # Contributed, collaborated, worked on
    SUPPORT = "SUPPORT"  # Assisted, supported, helped
    PASSIVE = "PASSIVE"  # Familiar with, knowledge of, exposed to


@dataclass
class EnhancedSkillEvidence(SkillEvidence):
    """Extended skill evidence with hands-on experience indicators."""
    experience_depth: ExperienceDepth = ExperienceDepth.NOT_FOUND
    has_metrics: bool = False  # Does evidence include measurable outcomes?
    has_outcomes: bool = False  # Does evidence describe results/impact?
    project_duration_months: Optional[int] = None  # Estimated project duration
    verb_intensity: ActionVerbIntensity = ActionVerbIntensity.PASSIVE
    hands_on_score: float = 0.0  # 0.0-1.0 score for hands-on depth


@dataclass
class EnhancedSkillValidationResult(SkillValidationResult):
    """Extended validation result with experience depth analysis."""
    experience_depth: ExperienceDepth = ExperienceDepth.NOT_FOUND
    hands_on_score: float = 0.0  # Overall hands-on experience score (0.0-1.0)
    priority_skill: bool = False  # Is this a user-specified priority skill?
    enhanced_evidence: List[EnhancedSkillEvidence] = field(default_factory=list)


class EnhancedActionVerbDetector:
    """
    Enhanced action verb detection with intensity classification.
    Identifies leadership, core delivery, contribution, and passive verbs.
    """

    # Action verbs grouped by intensity and hands-on depth
    LEADERSHIP_VERBS = {
        "led", "architected", "designed", "owned", "pioneered", "spearheaded",
        "established", "founded", "initiated", "drove", "directed", "managed"
    }
    CORE_DELIVERY_VERBS = {
        "built", "implemented", "developed", "created", "deployed", "engineered",
        "produced", "delivered", "launched", "released", "published", "shipped",
        "coded", "programmed", "constructed", "assembled", "integrated"
    }
    CONTRIBUTION_VERBS = {
        "contributed", "collaborated", "worked", "participated", "assisted",
        "supported", "helped", "cooperated", "coordinated", "facilitated",
        "enhanced", "improved", "optimized", "maintained", "updated"
    }
    SUPPORT_VERBS = {
        "aided", "backed", "bolstered", "reinforced", "troubleshot",
        "debugged", "tested", "reviewed", "monitored", "analyzed"
    }
    PASSIVE_VERBS = {
        "familiar with", "knowledge of", "aware of",
        "exposed to", "studied", "learned", "trained in",
        "basic understanding", "novice", "beginner", "introduction to"
    }

    @classmethod
    def detect_verbs_with_intensity(cls, text: str) -> Tuple[List[str], ActionVerbIntensity, float]:
        """
        Detect action verbs and classify intensity.
        Args:
            text: Text to analyze
        Returns:
            Tuple of (found_verbs, highest_intensity, hands_on_score)
        """
        text_lower = text.lower()
        found_verbs: List[str] = []
        highest_intensity = ActionVerbIntensity.PASSIVE
        intensity_score = 0.0

        # Highest to lower precedence
        for verb in cls.LEADERSHIP_VERBS:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.append(verb)
                if highest_intensity.value != ActionVerbIntensity.LEADERSHIP.value:
                    highest_intensity = ActionVerbIntensity.LEADERSHIP
                intensity_score = max(intensity_score, 1.0)

        for verb in cls.CORE_DELIVERY_VERBS:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.append(verb)
                if highest_intensity not in (ActionVerbIntensity.LEADERSHIP,):
                    highest_intensity = ActionVerbIntensity.CORE_DELIVERY
                intensity_score = max(intensity_score, 0.85)

        for verb in cls.CONTRIBUTION_VERBS:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.append(verb)
                if highest_intensity not in (ActionVerbIntensity.LEADERSHIP, ActionVerbIntensity.CORE_DELIVERY):
                    highest_intensity = ActionVerbIntensity.CONTRIBUTION
                intensity_score = max(intensity_score, 0.6)

        for verb in cls.SUPPORT_VERBS:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.append(verb)
                if highest_intensity not in (
                    ActionVerbIntensity.LEADERSHIP,
                    ActionVerbIntensity.CORE_DELIVERY,
                    ActionVerbIntensity.CONTRIBUTION
                ):
                    highest_intensity = ActionVerbIntensity.SUPPORT
                intensity_score = max(intensity_score, 0.4)

        for verb in cls.PASSIVE_VERBS:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.append(verb)
                # passive keeps the lowest score

        if not found_verbs or highest_intensity == ActionVerbIntensity.PASSIVE:
            intensity_score = max(intensity_score, 0.2)

        return found_verbs, highest_intensity, intensity_score


class MetricsAndOutcomesDetector:
    """
    Detects measurable outcomes, metrics, and quantifiable achievements
    in resume content to validate hands-on experience.
    """

    # Patterns for metrics and outcomes
    METRIC_PATTERNS = {
        "percentage": r'\b\d+%',  # e.g., "improved by 40%"
        "reduction": r'\b(?:reduced|decreased|cut|lowered)(?:\s+by)?\s+\d+%',
        "improvement": r'\b(?:improved|increased|boosted|enhanced)(?:\s+by)?\s+\d+%',
        "time_metric": r'\b\d+(?:\.\d+)?\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?)',
        "money_saved": r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:k|K|M|million|thousand))?',
        "users": r'\b\d+(?:k|K|M)?\s+(?:users?|customers?|clients?)',
        "scale": r'\b\d+(?:k|K|M)?\s+(?:requests?|transactions?|records?|rows?)',
    }
    OUTCOME_KEYWORDS = {
        "deployed", "launched", "shipped", "released", "delivered",
        "production", "live", "operational", "successful", "achieved",
        "completed", "finished", "resolved", "solved", "fixed"
    }

    @classmethod
    def detect_metrics_and_outcomes(cls, text: str) -> Tuple[bool, bool, List[str]]:
        """
        Detect metrics and outcomes in text.
        Args:
            text: Text to analyze
        Returns:
            Tuple of (has_metrics, has_outcomes, found_metrics)
        """
        has_metrics = False
        found_metrics: List[str] = []

        # Metrics
        for _, pattern in cls.METRIC_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                has_metrics = True
                found_metrics.extend(matches[:2])  # keep first 2 examples

        # Outcomes
        has_outcomes = any(
            re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE)
            for keyword in cls.OUTCOME_KEYWORDS
        )
        return has_metrics, has_outcomes, found_metrics


class ProjectDurationEstimator:
    """
    Estimates project duration from resume text patterns.
    Looks for date ranges, duration keywords, and temporal indicators.
    """

    # Duration patterns
    DURATION_PATTERNS = {
        "months": r'\b(\d+)\s*(?:month|mo)s?\b',
        "years": r'\b(\d+)\s*(?:year|yr)s?\b',
        "date_range": r'\b(\d{4})\s*[\-\u2013]\s*(\d{4})\b',  # e.g., "2021 - 2023"
        "month_year": r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[\-\u2013]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
    }

    @classmethod
    def estimate_duration(cls, text: str) -> Optional[int]:
        """
        Estimate project duration in months.
        Args:
            text: Text to analyze
        Returns:
            Estimated duration in months, or None if not detected
        """
        # explicit month duration
        month_match = re.search(cls.DURATION_PATTERNS["months"], text, re.IGNORECASE)
        if month_match:
            return int(month_match.group(1))

        # year duration -> months
        year_match = re.search(cls.DURATION_PATTERNS["years"], text, re.IGNORECASE)
        if year_match:
            return int(year_match.group(1)) * 12

        # date range (year-year)
        date_range_match = re.search(cls.DURATION_PATTERNS["date_range"], text)
        if date_range_match:
            start_year = int(date_range_match.group(1))
            end_year = int(date_range_match.group(2))
            return max(0, (end_year - start_year)) * 12

        return None


class EnhancedSkillContextValidator:
    """
    Enhanced validator that assesses hands-on experience depth
    beyond just semantic matching.
    """

    # Thresholds for experience depth classification
    EXPERT_THRESHOLD = 0.85
    PROFICIENT_THRESHOLD = 0.70
    COMPETENT_THRESHOLD = 0.55
    BASIC_THRESHOLD = 0.40

    def __init__(self, embedding_matcher: Optional[SemanticEmbeddingMatcher] = None):
        """Initialize enhanced validator."""
        self.matcher = embedding_matcher or SemanticEmbeddingMatcher()

    def validate_skill_with_depth(
        self,
        skill_name: str,
        resume_sections: Dict[str, str],
        section_contexts: Dict[str, ContextType],
        is_priority: bool = False
    ) -> EnhancedSkillValidationResult:
        """
        Validate skill with hands-on experience depth analysis.
        Args:
            skill_name: Skill to validate
            resume_sections: Resume sections
            section_contexts: Context type mapping
            is_priority: Is this a user-specified priority skill?
        Returns:
            EnhancedSkillValidationResult with depth analysis
        """
        result = EnhancedSkillValidationResult(
            skill_name=skill_name,
            jd_required=False,
            status=SkillValidationStatus.NOT_FOUND,
            resume_found=False,
            relevance_score=0.0,
            priority_skill=is_priority
        )
        enhanced_evidence_list: List[EnhancedSkillEvidence] = []

        # Search in all sections (prioritize project/experience over skills)
        for section_name, section_content in resume_sections.items():
            if not section_content:
                continue
            context_type = section_contexts.get(section_name, ContextType.UNKNOWN)

            # Find skill mentions
            similarity, matched_text = self._find_skill_in_section(
                skill_name, section_content
            )
            if similarity > 0:
                # Analyze hands-on depth
                enhanced_evidence = self._analyze_hands_on_depth(
                    skill_name=skill_name,
                    evidence_text=matched_text,
                    context_type=context_type,
                    semantic_similarity=similarity,
                    section_name=section_name
                )
                enhanced_evidence_list.append(enhanced_evidence)

        if not enhanced_evidence_list:
            result.status = SkillValidationStatus.NOT_FOUND
            result.experience_depth = ExperienceDepth.NOT_FOUND
            result.reasoning = f"'{skill_name}' not mentioned in resume."
            return result

        # Filter: ignore skills-only evidence if real experience exists
        non_skills_evidence = [
            e for e in enhanced_evidence_list
            if e.context_type != ContextType.SKILLS_SECTION
        ]
        if not non_skills_evidence:
            # Skill only in standalone Skills section
            result.status = SkillValidationStatus.IGNORED_STANDALONE
            result.resume_found = True
            result.experience_depth = ExperienceDepth.MENTIONED_ONLY
            result.relevance_score = 0.0
            result.enhanced_evidence = enhanced_evidence_list
            result.reasoning = (
                f"'{skill_name}' found only in Skills section with no supporting "
                "project or hands-on experience context."
            )
            return result

        # Use best evidence from project/experience
        best_evidence = max(non_skills_evidence, key=lambda e: e.hands_on_score)
        result.enhanced_evidence = [best_evidence] + [e for e in non_skills_evidence if e != best_evidence]
        result.resume_found = True
        result.hands_on_score = best_evidence.hands_on_score
        result.relevance_score = best_evidence.confidence_score
        result.experience_depth = best_evidence.experience_depth

        # Determine validation status based on hands-on score
        if best_evidence.hands_on_score >= self.EXPERT_THRESHOLD:
            result.status = SkillValidationStatus.VALIDATED
            result.reasoning = (
                f"'{skill_name}' validated with EXPERT-level hands-on experience "
                f"in {best_evidence.context_type.value.lower()} "
                f"(hands-on score: {best_evidence.hands_on_score:.1%}). "
                f"Evidence: {best_evidence.verb_intensity.value} verbs, "
                f"{'metrics present' if best_evidence.has_metrics else 'no metrics'}."
            )
        elif best_evidence.hands_on_score >= self.PROFICIENT_THRESHOLD:
            result.status = SkillValidationStatus.VALIDATED
            result.reasoning = (
                f"'{skill_name}' validated with PROFICIENT hands-on experience "
                f"(hands-on score: {best_evidence.hands_on_score:.1%}). "
                f"Evidence shows {best_evidence.verb_intensity.value.lower()} level usage."
            )
        elif best_evidence.hands_on_score >= self.COMPETENT_THRESHOLD:
            result.status = SkillValidationStatus.VALIDATED
            result.reasoning = (
                f"'{skill_name}' validated with COMPETENT hands-on experience "
                f"(hands-on score: {best_evidence.hands_on_score:.1%})."
            )
        elif best_evidence.hands_on_score >= self.BASIC_THRESHOLD:
            result.status = SkillValidationStatus.WEAK_EVIDENCE
            result.reasoning = (
                f"'{skill_name}' has BASIC evidence of hands-on use "
                f"(hands-on score: {best_evidence.hands_on_score:.1%}). "
                "Recommend manual verification for depth of expertise."
            )
        else:
            result.status = SkillValidationStatus.WEAK_EVIDENCE
            result.reasoning = (
                f"'{skill_name}' mentioned but lacks strong hands-on evidence "
                f"(hands-on score: {best_evidence.hands_on_score:.1%})."
            )
        return result

    def _analyze_hands_on_depth(
        self,
        skill_name: str,
        evidence_text: str,
        context_type: ContextType,
        semantic_similarity: float,
        section_name: str
    ) -> EnhancedSkillEvidence:
        """
        Analyze hands-on depth of evidence.
        Args:
            skill_name: Skill being analyzed
            evidence_text: Evidence text
            context_type: Context type
            semantic_similarity: Semantic similarity score
            section_name: Section name
        Returns:
            EnhancedSkillEvidence with hands-on analysis
        """
        # Detect action verbs with intensity
        verbs, intensity, verb_score = EnhancedActionVerbDetector.detect_verbs_with_intensity(
            evidence_text
        )
        # Detect metrics and outcomes
        has_metrics, has_outcomes, _ = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(
            evidence_text
        )
        # Estimate project duration
        duration_months = ProjectDurationEstimator.estimate_duration(evidence_text)

        # Calculate hands-on score (weighted combination)
        hands_on_score = self._calculate_hands_on_score(
            semantic_similarity=semantic_similarity,
            verb_score=verb_score,
            has_metrics=has_metrics,
            has_outcomes=has_outcomes,
            duration_months=duration_months,
            context_type=context_type
        )

        # Determine experience depth
        if hands_on_score >= self.EXPERT_THRESHOLD:
            experience_depth = ExperienceDepth.EXPERT
        elif hands_on_score >= self.PROFICIENT_THRESHOLD:
            experience_depth = ExperienceDepth.PROFICIENT
        elif hands_on_score >= self.COMPETENT_THRESHOLD:
            experience_depth = ExperienceDepth.COMPETENT
        elif hands_on_score >= self.BASIC_THRESHOLD:
            experience_depth = ExperienceDepth.BASIC
        else:
            experience_depth = ExperienceDepth.MENTIONED_ONLY

        return EnhancedSkillEvidence(
            skill_name=skill_name,
            context_type=context_type,
            evidence_text=evidence_text[:300],  # truncate
            confidence_score=semantic_similarity,
            location=section_name,
            action_verbs=verbs,
            experience_depth=experience_depth,
            has_metrics=has_metrics,
            has_outcomes=has_outcomes,
            project_duration_months=duration_months,
            verb_intensity=intensity,
            hands_on_score=hands_on_score
        )

    def _calculate_hands_on_score(
        self,
        semantic_similarity: float,
        verb_score: float,
        has_metrics: bool,
        has_outcomes: bool,
        duration_months: Optional[int],
        context_type: ContextType
    ) -> float:
        """
        Calculate comprehensive hands-on experience score.
        Weighted factors:
        - Semantic similarity: 30%
        - Action verb intensity: 30%
        - Metrics presence: 15%
        - Outcomes presence: 10%
        - Project duration: 10%
        - Context type: 5%
        """
        score = 0.0

        # Semantic similarity (30%)
        score += semantic_similarity * 0.30

        # Action verb intensity (30%)
        score += verb_score * 0.30

        # Metrics presence (15%)
        if has_metrics:
            score += 0.15

        # Outcomes presence (10%)
        if has_outcomes:
            score += 0.10

        # Project duration (10%)
        if duration_months is not None:
            if duration_months >= 12:
                score += 0.10  # 1+ year
            elif duration_months >= 6:
                score += 0.07  # 6+ months
            elif duration_months >= 3:
                score += 0.05  # 3+ months
            else:
                score += 0.03  # < 3 months

        # Context type bonus (5%)
        if context_type == ContextType.PROJECT:
            score += 0.05
        elif context_type == ContextType.WORK_EXPERIENCE:
            score += 0.04
        elif context_type == ContextType.RESPONSIBILITY:
            score += 0.03

        return min(score, 1.0)

    def _find_skill_in_section(
        self,
        skill_name: str,
        section_content: str,
        context_window: int = 250
    ) -> Tuple[float, str]:
        """Find skill in section with extended context window."""
        # Direct keyword match first
        skill_pattern = re.compile(r'\b' + re.escape(skill_name) + r'\b', re.IGNORECASE)
        match = skill_pattern.search(section_content)
        if match:
            # Extract larger context window for hands-on analysis
            start = max(0, match.start() - context_window)
            end = min(len(section_content), match.end() + context_window)
            context_text = section_content[start:end].strip()
            similarity = self.matcher.compute_similarity(skill_name, context_text)
            return similarity, context_text

        # Semantic search on chunks
        chunks = self._chunk_text(section_content, chunk_size=400, overlap=150)
        best_match, best_score = self.matcher.find_best_match(
            skill_name,
            chunks,
            threshold=0.50
        )
        if best_match:
            return best_score, best_match
        return 0.0, ""

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 150) -> List[str]:
        """Split text into overlapping chunks."""
        chunks: List[str] = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i: i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks


class EnhancedSemanticSkillMatcher:
    """
    Enhanced semantic skill matcher with hands-on experience validation
    and user-configurable priority skills.
    """

    def __init__(
        self,
        embedding_matcher: Optional[SemanticEmbeddingMatcher] = None,
        validator: Optional[EnhancedSkillContextValidator] = None
    ):
        """Initialize enhanced matcher."""
        self.matcher = embedding_matcher or SemanticEmbeddingMatcher()
        self.validator = validator or EnhancedSkillContextValidator(self.matcher)
        self.extractor = ResumeSectionExtractor()

    def analyze_with_priorities(
        self,
        jd_text: str,
        resume_text: str,
        jd_skills: Optional[List[str]] = None,
        priority_skills: Optional[List[str]] = None
    ) -> SkillMatchingReport:
        """
        Perform enhanced skill matching with priority skills.

        CHANGE: Evaluate the UNION of JD-extracted skills and user-entered
        priority skills so priorities are respected even if the JD does not
        mention them verbatim.
        """
        # 1) Extract JD skills if not provided
        if not jd_skills:
            jd_skills = self._extract_skills_from_jd(jd_text)
        
        # 1.5) FILTER OUT FALSE POSITIVES (locations, job titles, etc.)
        jd_skills = SkillFilter.filter_skills(jd_skills)

        # 2) Normalize priority list/set (generic, no hardcoded aliases)
        priority_skills = priority_skills or []
        # Also filter priority skills
        priority_skills = SkillFilter.filter_skills(priority_skills)
        priority_set = set(s.lower().strip() for s in priority_skills)

        # 3) Build evaluation list: UNION(JD skills, Priority skills) preserving display casing
        eval_skills: List[str] = []
        seen: Set[str] = set()
        for s in jd_skills:
            key = s.lower().strip()
            if key not in seen:
                eval_skills.append(s.strip())
                seen.add(key)
        for p in priority_skills:
            key = p.lower().strip()
            if key not in seen:
                eval_skills.append(p.strip())
                seen.add(key)

        # 4) Prepare resume sections and contexts
        resume_sections = self.extractor.extract_sections(resume_text)
        section_contexts = {
            section: self.extractor.identify_context_type(section)
            for section in resume_sections.keys()
        }

        # 5) Validate each skill with depth analysis
        validated_skills: List[EnhancedSkillValidationResult] = []
        ignored_skills: List[EnhancedSkillValidationResult] = []
        missing_skills: List[EnhancedSkillValidationResult] = []
        weak_skills: List[EnhancedSkillValidationResult] = []
        jd_set_lc = {s.lower().strip() for s in jd_skills}

        for skill in eval_skills:
            key = skill.lower().strip()
            is_priority = key in priority_set
            result = self.validator.validate_skill_with_depth(
                skill, resume_sections, section_contexts, is_priority
            )
            # Mark whether this skill originated from the JD or was priority-only
            result.jd_required = key in jd_set_lc

            if result.status == SkillValidationStatus.VALIDATED:
                validated_skills.append(result)
            elif result.status == SkillValidationStatus.IGNORED_STANDALONE:
                ignored_skills.append(result)
            elif result.status == SkillValidationStatus.NOT_FOUND:
                missing_skills.append(result)
            elif result.status == SkillValidationStatus.WEAK_EVIDENCE:
                weak_skills.append(result)

        # Sort by priority and hands-on score
        validated_skills.sort(key=lambda s: (not s.priority_skill, -s.hands_on_score))

        # Calculate overall relevance (weighted by priority) using the evaluated set size
        overall_score = self._calculate_weighted_relevance(
            validated_skills, weak_skills, missing_skills, len(eval_skills), priority_set
        )

        # Generate enhanced recommendations / summary
        recommendations = self._generate_enhanced_recommendations(
            validated_skills, ignored_skills, missing_skills, weak_skills, priority_set
        )
        resume_summary = self._create_enhanced_summary(
            resume_sections, validated_skills, priority_set
        )

        return SkillMatchingReport(
            overall_relevance_score=overall_score,
            total_jd_skills=len(eval_skills),  # evaluated set size
            validated_skills=validated_skills,
            ignored_skills=ignored_skills,
            missing_skills=missing_skills,
            weak_skills=weak_skills,
            resume_summary=resume_summary,
            recommendations=recommendations
        )

    def _calculate_weighted_relevance(
        self,
        validated: List[EnhancedSkillValidationResult],
        weak: List[EnhancedSkillValidationResult],
        missing: List[EnhancedSkillValidationResult],
        total_jd_skills: int,
        priority_skills: Set[str]
    ) -> float:
        """Calculate relevance with priority skill weighting."""
        if total_jd_skills == 0:
            return 0.0

        score = 0.0

        # Validated skills add hands-on score; priority skills are weighted heavier
        for skill in validated:
            weight = 1.5 if skill.priority_skill else 1.0
            score += (skill.hands_on_score or 0.0) * weight

        # Weak evidence contributes a smaller constant; prioritize weak priority skills slightly
        for skill in weak:
            weight = 1.3 if skill.priority_skill else 1.0
            score += 0.4 * weight

        # Penalize missing priority skills more heavily
        missing_priority_count = sum(
            1 for s in missing if s.skill_name.lower() in priority_skills
        )
        penalty = missing_priority_count * 0.15

        raw_score = score / total_jd_skills
        return max(0.0, min(1.0, raw_score - penalty))

    def _generate_enhanced_recommendations(
        self,
        validated: List[EnhancedSkillValidationResult],
        ignored: List[EnhancedSkillValidationResult],
        missing: List[EnhancedSkillValidationResult],
        weak: List[EnhancedSkillValidationResult],
        priority_skills: Set[str]
    ) -> List[str]:
        """Generate enhanced recommendations."""
        recommendations: List[str] = []

        # Missing priority skills (critical)
        missing_priority = [
            s for s in missing if s.skill_name.lower() in priority_skills
        ]
        if missing_priority:
            skills_str = ", ".join(s.skill_name for s in missing_priority[:3])
            recommendations.append(
                f"🚨 CRITICAL: Missing priority skills: {skills_str}. "
                "Gaining hands-on experience with these is essential for this role."
            )

        # Weak evidence for priority skills
        weak_priority = [
            s for s in weak if s.skill_name.lower() in priority_skills
        ]
        if weak_priority:
            skills_str = ", ".join(s.skill_name for s in weak_priority[:2])
            recommendations.append(
                f"⚠️ Priority skills with weak evidence: {skills_str}. "
                "Add quantifiable project outcomes and metrics to strengthen."
            )

        # Skills listed only (no hands-on)
        if ignored:
            skills_str = ", ".join(s.skill_name for s in ignored[:3])
            recommendations.append(
                f"🗂️ Listed-only skills: {skills_str}. "
                "Add specific project examples showing hands-on usage."
            )

        # Missing non-priority skills
        missing_non_priority = [
            s for s in missing if s.skill_name.lower() not in priority_skills
        ]
        if missing_non_priority:
            skills_str = ", ".join(s.skill_name for s in missing_non_priority[:3])
            recommendations.append(
                f"Consider gaining exposure to: {skills_str}"
            )

        # Positive feedback for strong matches
        expert_skills = [
            s for s in validated
            if hasattr(s, 'experience_depth') and s.experience_depth == ExperienceDepth.EXPERT
        ]
        if len(expert_skills) >= 3:
            recommendations.append(
                "✅ Strong hands-on evidence demonstrated for "
                f"{len(expert_skills)} skills. Consider highlighting measurable outcomes in interview."
            )

        return recommendations

    def _create_enhanced_summary(
        self,
        resume_sections: Dict[str, str],
        validated_skills: List[EnhancedSkillValidationResult],
        priority_skills: Set[str]
    ) -> str:
        """Create enhanced resume summary."""
        summary_parts: List[str] = []

        if validated_skills:
            priority_validated = [
                s for s in validated_skills if s.priority_skill
            ]
            if priority_validated and len(priority_skills) > 0:
                summary_parts.append(
                    f"Validated {len(priority_validated)}/{len(priority_skills)} priority skills"
                )

            expert_count = sum(
                1 for s in validated_skills
                if hasattr(s, 'experience_depth') and s.experience_depth == ExperienceDepth.EXPERT
            )
            if expert_count > 0:
                summary_parts.append(f"{expert_count} expert-level skills")

        if "PROJECTS" in resume_sections:
            summary_parts.append("Detailed project portfolio present")

        return "; ".join(summary_parts) if summary_parts else "Basic resume structure"

    def _extract_skills_from_jd(self, jd_text: str) -> List[str]:
        """Extract skills from JD (reuse base implementation)."""
        from semantic_skill_matcher import SemanticSkillMatcher
        base_matcher = SemanticSkillMatcher()
        return base_matcher.extract_skills_from_jd(jd_text)


if __name__ == "__main__":
    # Example usage
    sample_jd = """
    Senior Python Developer needed for cloud-native projects.
    Required Skills:
    - Python (5+ years)
    - AWS (EC2, S3, Lambda)
    - PostgreSQL
    - Docker & Kubernetes
    - FastAPI
    - CI/CD pipelines
    """

    sample_resume = """
    PROFESSIONAL EXPERIENCE
    Senior Software Engineer \n TechCorp \n 2021-Present (2 years)
    - Architected and deployed microservices platform using Python and FastAPI
      serving 500K+ daily users with 99.9% uptime
    - Optimized PostgreSQL queries, reducing average response time by 45%
    - Led Kubernetes migration of legacy monolith, cutting infrastructure costs by 30%
    - Built CI/CD pipelines with GitHub Actions, reducing deployment time from 2 hours to 15 minutes
    Backend Developer \n StartupX \n 2019-2021 (2 years)
    - Developed Python REST APIs for customer analytics platform
    - Worked with AWS services (EC2, S3, Lambda) for serverless architecture
    - Collaborated on Docker containerization for development environments
    SKILLS
    Python, JavaScript, Java, PostgreSQL, MongoDB, Redis, Docker, Kubernetes,
    AWS, Azure, FastAPI, Django, Flask, React, Node.js, Git, Jenkins
    """

    matcher = EnhancedSemanticSkillMatcher()
    report = matcher.analyze_with_priorities(
        jd_text=sample_jd,
        resume_text=sample_resume,
        priority_skills=["Python", "AWS", "Kubernetes", "PostgreSQL"]  # any user-entered skills
    )

    print("=" * 80)
    print("ENHANCED SEMANTIC SKILL MATCHING REPORT")
    print("=" * 80)
    print(f"\nOverall Relevance Score: {report.overall_relevance_score:.1%}")
    print(f"Validated Skills: {len(report.validated_skills)}")
    print(f"Ignored Skills: {len(report.ignored_skills)}")
    print(f"Missing Skills: {len(report.missing_skills)}")
    print(f"Weak Evidence Skills: {len(report.weak_skills)}")
    print("\n" + "-" * 80)
    print("VALIDATED SKILLS (with Hands-On Evidence)")
    print("-" * 80)
    for skill in report.validated_skills:
        priority_marker = "🎯 PRIORITY" if getattr(skill, "priority_skill", False) else ""
        print(f"\n✅ {skill.skill_name} {priority_marker}")
        if hasattr(skill, 'hands_on_score'):
            print(f" Hands-On Score: {skill.hands_on_score:.1%}")
        if hasattr(skill, 'experience_depth'):
            print(f" Experience Depth: {skill.experience_depth.value}")
        print(f" {skill.reasoning}")

    print("\n" + "-" * 80)
    print("RECOMMENDATIONS")
    print("-" * 80)
    for i, rec in enumerate(report.recommendations, 1):
        print(f"{i}. {rec}")