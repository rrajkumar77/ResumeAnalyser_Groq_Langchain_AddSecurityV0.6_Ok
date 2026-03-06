"""
Skills Gap Analysis & Learning Path Recommendations
===================================================

Identifies near-miss candidates (60-80% fit) and recommends
targeted training paths instead of rejecting them outright.

Key Features:
- Detailed skills gap identification
- Learning resource recommendations (courses, projects)
- Timeline estimates for skill development
- Hire-Train-Deploy vs. Keep Searching recommendations
- Cost-benefit analysis for training investment

Use Case:
Candidate has 78% fit but missing Kubernetes expertise.
→ Recommend: Hire as Junior DevOps, 3-month K8s training, promote to DevOps Engineer
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from enhanced_semantic_matcher import (
    EnhancedSemanticSkillMatcher,
    SkillMatchingReport,
    ExperienceDepth
)


class SkillGapSeverity(Enum):
    """Severity of a skill gap."""
    CRITICAL = "CRITICAL"  # Priority skill missing entirely
    HIGH = "HIGH"  # Required skill missing or very weak
    MEDIUM = "MEDIUM"  # Nice-to-have skill missing
    LOW = "LOW"  # Minor enhancement opportunity


class LearningDifficulty(Enum):
    """Difficulty of learning a skill."""
    BEGINNER = "BEGINNER"  # Can learn in weeks
    INTERMEDIATE = "INTERMEDIATE"  # Requires months
    ADVANCED = "ADVANCED"  # Requires 6+ months


@dataclass
class LearningResource:
    """A learning resource (course, book, project)."""
    type: str  # "course", "book", "project", "certification"
    name: str
    provider: str  # "Udemy", "Coursera", "AWS", etc.
    duration_hours: int
    cost_usd: Optional[float] = None
    url: Optional[str] = None
    description: str = ""


@dataclass
class SkillGap:
    """Analysis of a single skill gap."""
    skill_name: str
    severity: SkillGapSeverity
    current_level: ExperienceDepth
    target_level: ExperienceDepth
    learning_difficulty: LearningDifficulty
    estimated_timeline_months: int
    learning_resources: List[LearningResource] = field(default_factory=list)
    practice_projects: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class LearningPath:
    """Complete learning path for closing skill gaps."""
    skill_gaps: List[SkillGap]
    total_timeline_months: int
    total_cost_usd: float
    recommended_sequence: List[str]  # Skills in order to learn
    milestones: List[Dict[str, str]]  # Checkpoints for progress
    

@dataclass
class HireTrainDecision:
    """Recommendation on whether to hire-train or keep searching."""
    decision: str  # "HIRE_AND_TRAIN", "KEEP_SEARCHING", "HIRE_AS_IS"
    reasoning: str
    recommended_role_level: str  # e.g., "Junior", "Mid-level", "Senior"
    training_investment_months: int
    target_role_after_training: str
    roi_estimate: str  # Return on investment estimate
    risks: List[str]
    conditions: List[str]  # Conditions for hire-train decision


@dataclass
class SkillsGapAnalysisReport:
    """Complete skills gap analysis and recommendations."""
    candidate_id: str
    current_fit_score: float
    projected_fit_score_after_training: float
    critical_gaps: List[SkillGap]
    high_priority_gaps: List[SkillGap]
    medium_priority_gaps: List[SkillGap]
    low_priority_gaps: List[SkillGap]
    existing_strengths: List[str]
    learning_path: LearningPath
    hire_train_decision: HireTrainDecision
    
    def get_all_gaps(self) -> List[SkillGap]:
        """Get all skill gaps sorted by severity."""
        return (self.critical_gaps + 
                self.high_priority_gaps + 
                self.medium_priority_gaps + 
                self.low_priority_gaps)
    
    def export_to_markdown(self) -> str:
        """Export to markdown format."""
        md = f"""# Skills Gap Analysis Report

**Candidate:** {self.candidate_id}  
**Current Fit Score:** {self.current_fit_score:.0%}  
**Projected Fit Score (After Training):** {self.projected_fit_score_after_training:.0%}

---

## Decision Summary

**Recommendation:** {self.hire_train_decision.decision}  
**Reasoning:** {self.hire_train_decision.reasoning}

**Recommended Hire Level:** {self.hire_train_decision.recommended_role_level}  
**Training Duration:** {self.hire_train_decision.training_investment_months} months  
**Target Role After Training:** {self.hire_train_decision.target_role_after_training}

**ROI Estimate:** {self.hire_train_decision.roi_estimate}

---

## Existing Strengths

{chr(10).join('- ' + s for s in self.existing_strengths)}

---

## Skills Gaps

### Critical Gaps (Priority Skills Missing)
"""
        for gap in self.critical_gaps:
            md += f"""
**{gap.skill_name}**
- Current Level: {gap.current_level.value}
- Target Level: {gap.target_level.value}
- Timeline: {gap.estimated_timeline_months} months
- Difficulty: {gap.learning_difficulty.value}
- {gap.reasoning}
"""
        
        if self.high_priority_gaps:
            md += "\n### High Priority Gaps\n"
            for gap in self.high_priority_gaps:
                md += f"- **{gap.skill_name}** ({gap.estimated_timeline_months} months to {gap.target_level.value})\n"
        
        md += f"""
---

## Learning Path

**Total Timeline:** {self.learning_path.total_timeline_months} months  
**Estimated Cost:** ${self.learning_path.total_cost_usd:,.2f}

**Recommended Sequence:**
{chr(10).join(f'{i+1}. {skill}' for i, skill in enumerate(self.learning_path.recommended_sequence))}

### Detailed Learning Resources
"""
        
        for gap in self.get_all_gaps()[:5]:  # Top 5 gaps
            if gap.learning_resources:
                md += f"\n#### {gap.skill_name}\n"
                for resource in gap.learning_resources:
                    md += f"- **{resource.name}** ({resource.provider}) - {resource.duration_hours}h"
                    if resource.cost_usd:
                        md += f" - ${resource.cost_usd:.2f}"
                    md += "\n"
        
        md += f"""
---

## Milestones & Checkpoints

{chr(10).join(f"**Month {m['month']}:** {m['milestone']}" for m in self.learning_path.milestones)}

---

## Risks & Conditions

### Risks
{chr(10).join('- ' + r for r in self.hire_train_decision.risks)}

### Conditions for Success
{chr(10).join('- ' + c for c in self.hire_train_decision.conditions)}
"""
        return md


class SkillsGapAnalyzer:
    """
    Analyzes skill gaps and recommends learning paths.
    """
    
    # Learning resource database (simplified - would be expanded)
    LEARNING_RESOURCES_DB = {
        "python": [
            LearningResource(
                type="course",
                name="Python for Everybody Specialization",
                provider="Coursera",
                duration_hours=120,
                cost_usd=49.0,
                description="Comprehensive Python fundamentals to intermediate"
            ),
            LearningResource(
                type="course",
                name="Advanced Python Programming",
                provider="Udemy",
                duration_hours=40,
                cost_usd=89.99,
                description="Deep dive into advanced Python concepts"
            ),
        ],
        "kubernetes": [
            LearningResource(
                type="course",
                name="Kubernetes for Developers",
                provider="Linux Foundation",
                duration_hours=40,
                cost_usd=299.0,
                description="Official Kubernetes training"
            ),
            LearningResource(
                type="certification",
                name="Certified Kubernetes Application Developer (CKAD)",
                provider="CNCF",
                duration_hours=100,
                cost_usd=395.0,
                description="Industry-recognized K8s certification"
            ),
        ],
        "aws": [
            LearningResource(
                type="course",
                name="AWS Certified Solutions Architect",
                provider="A Cloud Guru",
                duration_hours=60,
                cost_usd=47.0,
                description="Complete AWS architecture training"
            ),
        ],
        "postgresql": [
            LearningResource(
                type="course",
                name="PostgreSQL Database Administration",
                provider="Udemy",
                duration_hours=30,
                cost_usd=84.99,
                description="Database optimization and administration"
            ),
        ],
        "terraform": [
            LearningResource(
                type="course",
                name="HashiCorp Certified: Terraform Associate",
                provider="HashiCorp",
                duration_hours=40,
                cost_usd=199.0,
                description="Infrastructure as Code with Terraform"
            ),
        ],
    }
    
    # Practice project templates
    PRACTICE_PROJECTS = {
        "python": [
            "Build a REST API using FastAPI with authentication and database integration",
            "Create a data processing pipeline using pandas and SQLAlchemy",
            "Develop a web scraper with error handling and data validation"
        ],
        "kubernetes": [
            "Deploy a 3-tier web application on K8s with services and ingress",
            "Set up monitoring and logging with Prometheus and Grafana",
            "Implement blue-green deployment strategy"
        ],
        "aws": [
            "Build serverless API using Lambda, API Gateway, and DynamoDB",
            "Create auto-scaling web app with ECS, ALB, and RDS",
            "Implement CI/CD pipeline using CodePipeline and CodeBuild"
        ],
        "postgresql": [
            "Optimize slow queries on 10M+ row dataset",
            "Design and implement database sharding strategy",
            "Set up replication and failover"
        ],
        "terraform": [
            "Create reusable Terraform modules for AWS infrastructure",
            "Implement multi-environment deployment (dev/staging/prod)",
            "Build infrastructure for microservices on ECS"
        ],
    }
    
    def __init__(self):
        """Initialize skills gap analyzer."""
        self.matcher = EnhancedSemanticSkillMatcher()
    
    def analyze(
        self,
        jd_text: str,
        resume_text: str,
        priority_skills: Optional[List[str]] = None,
        candidate_id: str = "Candidate"
    ) -> SkillsGapAnalysisReport:
        """
        Perform complete skills gap analysis.
        
        Args:
            jd_text: Job Description text
            resume_text: Resume text
            priority_skills: Priority skills list
            candidate_id: Candidate identifier
            
        Returns:
            SkillsGapAnalysisReport
        """
        # Run skill matching analysis
        report = self.matcher.analyze_with_priorities(
            jd_text=jd_text,
            resume_text=resume_text,
            priority_skills=priority_skills
        )
        
        # Identify skill gaps by severity
        priority_set = set(s.lower().strip() for s in (priority_skills or []))
        
        critical_gaps = []
        high_priority_gaps = []
        medium_priority_gaps = []
        low_priority_gaps = []
        
        # Missing skills
        for skill in report.missing_skills:
            is_priority = skill.skill_name.lower() in priority_set
            
            gap = self._create_skill_gap(
                skill_name=skill.skill_name,
                current_level=ExperienceDepth.NOT_FOUND,
                target_level=ExperienceDepth.PROFICIENT,
                is_priority=is_priority
            )
            
            if is_priority:
                critical_gaps.append(gap)
            else:
                high_priority_gaps.append(gap)
        
        # Weak evidence skills
        for skill in report.weak_skills:
            is_priority = skill.skill_name.lower() in priority_set
            
            current_level = getattr(skill, 'experience_depth', ExperienceDepth.BASIC)
            
            gap = self._create_skill_gap(
                skill_name=skill.skill_name,
                current_level=current_level,
                target_level=ExperienceDepth.PROFICIENT,
                is_priority=is_priority
            )
            
            if is_priority:
                critical_gaps.append(gap)
            else:
                medium_priority_gaps.append(gap)
        
        # Ignored skills (skills section only)
        for skill in report.ignored_skills:
            gap = self._create_skill_gap(
                skill_name=skill.skill_name,
                current_level=ExperienceDepth.MENTIONED_ONLY,
                target_level=ExperienceDepth.COMPETENT,
                is_priority=False
            )
            low_priority_gaps.append(gap)
        
        # Identify existing strengths
        existing_strengths = [
            f"{s.skill_name} ({s.experience_depth.value if hasattr(s, 'experience_depth') else 'Validated'})"
            for s in report.validated_skills[:10]
        ]
        
        # Create learning path
        learning_path = self._create_learning_path(
            critical_gaps + high_priority_gaps[:3]  # Focus on top gaps
        )
        
        # Calculate projected fit score
        projected_fit = self._calculate_projected_fit(
            current_fit=report.overall_relevance_score,
            gaps_addressed=len(critical_gaps) + min(3, len(high_priority_gaps))
        )
        
        # Make hire-train decision
        hire_train_decision = self._make_hire_train_decision(
            current_fit=report.overall_relevance_score,
            projected_fit=projected_fit,
            critical_gaps_count=len(critical_gaps),
            high_gaps_count=len(high_priority_gaps),
            existing_strengths_count=len(report.validated_skills),
            training_months=learning_path.total_timeline_months
        )
        
        return SkillsGapAnalysisReport(
            candidate_id=candidate_id,
            current_fit_score=report.overall_relevance_score,
            projected_fit_score_after_training=projected_fit,
            critical_gaps=critical_gaps,
            high_priority_gaps=high_priority_gaps,
            medium_priority_gaps=medium_priority_gaps,
            low_priority_gaps=low_priority_gaps,
            existing_strengths=existing_strengths,
            learning_path=learning_path,
            hire_train_decision=hire_train_decision
        )
    
    def _create_skill_gap(
        self,
        skill_name: str,
        current_level: ExperienceDepth,
        target_level: ExperienceDepth,
        is_priority: bool
    ) -> SkillGap:
        """Create a SkillGap object."""
        # Determine severity
        if is_priority and current_level == ExperienceDepth.NOT_FOUND:
            severity = SkillGapSeverity.CRITICAL
        elif current_level == ExperienceDepth.NOT_FOUND:
            severity = SkillGapSeverity.HIGH
        elif current_level in (ExperienceDepth.BASIC, ExperienceDepth.MENTIONED_ONLY):
            severity = SkillGapSeverity.MEDIUM
        else:
            severity = SkillGapSeverity.LOW
        
        # Estimate timeline and difficulty
        timeline_months, difficulty = self._estimate_learning_time(
            current_level, target_level
        )
        
        # Get learning resources
        resources = self._get_learning_resources(skill_name, current_level, target_level)
        
        # Get practice projects
        projects = self._get_practice_projects(skill_name)
        
        # Generate reasoning
        reasoning = self._generate_gap_reasoning(
            skill_name, current_level, target_level, is_priority
        )
        
        return SkillGap(
            skill_name=skill_name,
            severity=severity,
            current_level=current_level,
            target_level=target_level,
            learning_difficulty=difficulty,
            estimated_timeline_months=timeline_months,
            learning_resources=resources,
            practice_projects=projects,
            reasoning=reasoning
        )
    
    def _estimate_learning_time(
        self,
        current_level: ExperienceDepth,
        target_level: ExperienceDepth
    ) -> Tuple[int, LearningDifficulty]:
        """Estimate learning timeline and difficulty."""
        # Define progression matrix (months to reach target)
        progression = {
            (ExperienceDepth.NOT_FOUND, ExperienceDepth.BASIC): (1, LearningDifficulty.BEGINNER),
            (ExperienceDepth.NOT_FOUND, ExperienceDepth.COMPETENT): (3, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.NOT_FOUND, ExperienceDepth.PROFICIENT): (6, LearningDifficulty.ADVANCED),
            (ExperienceDepth.NOT_FOUND, ExperienceDepth.EXPERT): (12, LearningDifficulty.ADVANCED),
            (ExperienceDepth.MENTIONED_ONLY, ExperienceDepth.COMPETENT): (2, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.MENTIONED_ONLY, ExperienceDepth.PROFICIENT): (4, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.BASIC, ExperienceDepth.COMPETENT): (2, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.BASIC, ExperienceDepth.PROFICIENT): (4, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.COMPETENT, ExperienceDepth.PROFICIENT): (3, LearningDifficulty.INTERMEDIATE),
            (ExperienceDepth.COMPETENT, ExperienceDepth.EXPERT): (6, LearningDifficulty.ADVANCED),
        }
        
        return progression.get((current_level, target_level), (3, LearningDifficulty.INTERMEDIATE))
    
    def _get_learning_resources(
        self,
        skill_name: str,
        current_level: ExperienceDepth,
        target_level: ExperienceDepth
    ) -> List[LearningResource]:
        """Get learning resources for a skill."""
        skill_lower = skill_name.lower()
        
        # Check if we have resources for this skill
        for key in self.LEARNING_RESOURCES_DB:
            if key in skill_lower:
                return self.LEARNING_RESOURCES_DB[key]
        
        # Generic resource
        return [
            LearningResource(
                type="course",
                name=f"{skill_name} Fundamentals",
                provider="Online Learning Platform",
                duration_hours=40,
                cost_usd=99.0,
                description=f"Comprehensive {skill_name} training"
            )
        ]
    
    def _get_practice_projects(self, skill_name: str) -> List[str]:
        """Get practice projects for a skill."""
        skill_lower = skill_name.lower()
        
        for key in self.PRACTICE_PROJECTS:
            if key in skill_lower:
                return self.PRACTICE_PROJECTS[key]
        
        return [
            f"Build a small project using {skill_name}",
            f"Contribute to an open-source {skill_name} project",
            f"Complete {skill_name} coding challenges"
        ]
    
    def _generate_gap_reasoning(
        self,
        skill_name: str,
        current_level: ExperienceDepth,
        target_level: ExperienceDepth,
        is_priority: bool
    ) -> str:
        """Generate reasoning for the gap."""
        if is_priority and current_level == ExperienceDepth.NOT_FOUND:
            return f"Critical: {skill_name} is a priority skill and is completely missing from resume."
        elif current_level == ExperienceDepth.NOT_FOUND:
            return f"High priority: {skill_name} required for role but not found in resume."
        elif current_level == ExperienceDepth.MENTIONED_ONLY:
            return f"{skill_name} listed in skills section but no hands-on project evidence."
        elif current_level == ExperienceDepth.BASIC:
            return f"{skill_name} has minimal hands-on experience. Needs deeper expertise."
        else:
            return f"{skill_name} proficiency can be enhanced to {target_level.value} level."
    
    def _create_learning_path(self, skill_gaps: List[SkillGap]) -> LearningPath:
        """Create a learning path from skill gaps."""
        # Sort by severity and timeline
        sorted_gaps = sorted(
            skill_gaps,
            key=lambda g: (g.severity.value, g.estimated_timeline_months)
        )
        
        # Calculate totals
        total_timeline = sum(g.estimated_timeline_months for g in sorted_gaps)
        # Adjust for parallel learning (assume 30% overlap)
        total_timeline = int(total_timeline * 0.7)
        
        total_cost = sum(
            sum(r.cost_usd or 0 for r in g.learning_resources)
            for g in sorted_gaps
        )
        
        # Create sequence (critical first, then by learning difficulty)
        sequence = [g.skill_name for g in sorted_gaps]
        
        # Create milestones
        milestones = []
        month = 0
        for gap in sorted_gaps:
            month += gap.estimated_timeline_months
            milestones.append({
                "month": str(month),
                "milestone": f"Achieve {gap.target_level.value} level in {gap.skill_name}"
            })
        
        return LearningPath(
            skill_gaps=sorted_gaps,
            total_timeline_months=total_timeline,
            total_cost_usd=total_cost,
            recommended_sequence=sequence,
            milestones=milestones
        )
    
    def _calculate_projected_fit(
        self,
        current_fit: float,
        gaps_addressed: int
    ) -> float:
        """Calculate projected fit score after training."""
        # Each gap addressed adds ~8-12% to fit score
        improvement_per_gap = 0.10
        projected = current_fit + (gaps_addressed * improvement_per_gap)
        return min(projected, 1.0)
    
    def _make_hire_train_decision(
        self,
        current_fit: float,
        projected_fit: float,
        critical_gaps_count: int,
        high_gaps_count: int,
        existing_strengths_count: int,
        training_months: int
    ) -> HireTrainDecision:
        """Make hire-train vs. keep-searching decision."""
        # Decision matrix
        if current_fit >= 0.75 and critical_gaps_count == 0:
            decision = "HIRE_AS_IS"
            role_level = "Mid-level to Senior"
            training_investment = 0
            target_role = "Current target role"
            reasoning = "Strong fit with no critical gaps. Candidate ready for immediate hire."
            risks = ["None significant"]
            conditions = ["Standard onboarding process"]
            
        elif 0.60 <= current_fit < 0.75 and projected_fit >= 0.85 and training_months <= 6:
            decision = "HIRE_AND_TRAIN"
            if current_fit >= 0.70:
                role_level = "Mid-level (with training path)"
            else:
                role_level = "Junior to Mid-level (with training path)"
            
            training_investment = training_months
            target_role = "Target senior role after training"
            reasoning = (f"Good foundation ({current_fit:.0%} fit) with {existing_strengths_count} validated strengths. "
                        f"Projected to reach {projected_fit:.0%} fit after {training_months} months of training. "
                        f"ROI positive given training investment.")
            risks = [
                "Candidate may leave after training (retention risk)",
                "Training timeline may extend beyond estimate",
                "Performance during training period uncertain"
            ]
            conditions = [
                "Structured training program with clear milestones",
                "Mentorship and hands-on project assignments",
                "Regular progress assessments (monthly check-ins)",
                "Retention agreement or training cost repayment clause"
            ]
            
        elif current_fit < 0.60 or critical_gaps_count > 2 or training_months > 9:
            decision = "KEEP_SEARCHING"
            role_level = "N/A"
            training_investment = 0
            target_role = "N/A"
            reasoning = (f"Current fit too low ({current_fit:.0%}) or training investment too high "
                        f"({training_months} months with {critical_gaps_count} critical gaps). "
                        f"More cost-effective to find better-matched candidate.")
            risks = ["N/A"]
            conditions = ["N/A"]
            
        else:
            decision = "HIRE_AND_TRAIN"
            role_level = "Junior (with aggressive training)"
            training_investment = training_months
            target_role = "Mid-level role after training"
            reasoning = "Marginal case requiring significant investment. Consider only if talent market is tight."
            risks = [
                "High training investment with uncertain return",
                "Extended ramp-up time",
                "May not reach target proficiency"
            ]
            conditions = [
                "Very tight talent market with no better options",
                "Strong cultural fit and learning aptitude demonstrated",
                "Willingness to commit to extended training period",
                "Lower initial compensation commensurate with junior level"
            ]
        
        # ROI estimate
        if decision == "HIRE_AS_IS":
            roi = "Immediate productivity"
        elif decision == "HIRE_AND_TRAIN":
            roi = f"Productivity ramp-up over {training_investment} months. Break-even at month {training_investment + 3}"
        else:
            roi = "N/A - Continue search"
        
        return HireTrainDecision(
            decision=decision,
            reasoning=reasoning,
            recommended_role_level=role_level,
            training_investment_months=training_investment,
            target_role_after_training=target_role,
            roi_estimate=roi,
            risks=risks,
            conditions=conditions
        )


if __name__ == "__main__":
    # Example usage
    print("Skills Gap Analyzer - Ready for Integration")
