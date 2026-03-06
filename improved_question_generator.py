"""
Enhanced Interview Question Generator
=====================================

Improvements over base version:
1. ✅ Clean, readable formatting
2. ✅ Specific technical questions (not generic)
3. ✅ Context-aware (based on actual resume evidence)
4. ✅ Detailed answer guides with examples
5. ✅ Follow-up probing questions
6. ✅ Clear evaluation criteria
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from enhanced_semantic_matcher import (
    EnhancedSemanticSkillMatcher,
    EnhancedSkillValidationResult,
    ExperienceDepth,
    ActionVerbIntensity
)


class LifecyclePhase(Enum):
    """Project lifecycle phases."""
    REQUIREMENTS = "Requirements & Planning"
    DESIGN = "Design & Architecture"
    DEVELOPMENT = "Development & Implementation"
    TESTING = "Testing & Quality Assurance"
    DEPLOYMENT = "Deployment & Operations"


@dataclass
class InterviewQuestion:
    """Enhanced interview question with detailed guidance."""
    lifecycle_phase: LifecyclePhase
    skill: str
    question: str
    context_from_resume: str  # What the candidate claimed
    answer_guide: Dict[str, List[str]]
    difficulty: str
    follow_up_questions: List[str] = field(default_factory=list)
    evaluation_rubric: Dict[str, str] = field(default_factory=dict)
    
    def format_for_interviewer(self) -> str:
        """Format question for interviewer use."""
        output = f"""
{'='*80}
📌 SKILL: {self.skill} | DIFFICULTY: {self.difficulty}
PHASE: {self.lifecycle_phase.value}
{'='*80}

📋 CANDIDATE'S CLAIM (from resume):
"{self.context_from_resume}"

❓ INTERVIEW QUESTION:
{self.question}

{'─'*80}
✅ WHAT TO LISTEN FOR:

Key Concepts:
{chr(10).join('  • ' + c for c in self.answer_guide.get('concepts', []))}

Specific Tools/Technologies:
{chr(10).join('  • ' + t for t in self.answer_guide.get('tools', []))}

Techniques & Approaches:
{chr(10).join('  • ' + t for t in self.answer_guide.get('techniques', []))}

Expected Depth Indicators (Hands-On Signs):
{chr(10).join('  ✓ ' + i for i in self.answer_guide.get('depth_indicators', []))}

{'─'*80}
🚩 RED FLAGS:
{chr(10).join('  ⚠️  ' + r for r in self.answer_guide.get('red_flags', []))}

{'─'*80}
🔍 FOLLOW-UP PROBING QUESTIONS:
{chr(10).join('  ' + str(i+1) + '. ' + q for i, q in enumerate(self.follow_up_questions))}

{'─'*80}
📊 EVALUATION RUBRIC:

Strong Answer (Hire):
{self.evaluation_rubric.get('strong', 'Demonstrates deep understanding with specific examples')}

Moderate Answer (Maybe):
{self.evaluation_rubric.get('moderate', 'Shows basic knowledge but lacks depth or specifics')}

Weak Answer (No Hire):
{self.evaluation_rubric.get('weak', 'Vague responses, cannot explain decisions, or contradicts resume')}

{'='*80}
"""
        return output


class ImprovedQuestionGenerator:
    """
    Generates better interview questions with:
    - Specific technical depth
    - Clear evaluation criteria
    - Evidence-based context
    """
    
    # Enhanced skill-specific question templates
    SKILL_QUESTIONS = {
        "sql": {
            "optimization": """
You mentioned optimizing SQL queries that {metric_claim}.

Walk me through a specific example:
1. What was the query doing initially?
2. How did you identify it was slow? (What tools did you use?)
3. What specific optimization techniques did you apply?
4. How did you validate the {metric_claim}?
5. Were there any trade-offs you had to consider?
""",
            "deployment": """
Tell me about your SQL deployment process for {context}.

Specifically:
1. How did you manage schema changes across environments (dev/staging/prod)?
2. What tools did you use for versioning and deployment?
3. How did you handle rollbacks if something went wrong?
4. How did you ensure zero-downtime deployments for schema changes?
""",
            "design": """
Describe how you designed the database schema for {context}.

I want to understand:
1. What normalization level did you choose and why?
2. How did you handle relationships between entities?
3. What indexing strategy did you implement?
4. How did you plan for scalability and performance?
"""
        },
        
        "adf": {
            "pipeline_design": """
You mentioned building data ingestion pipelines with Azure Data Factory for {context}.

Walk me through your approach:
1. How did you design the pipeline architecture?
2. What triggers did you use (scheduled, event-based, tumbling window)?
3. How did you handle error handling and retry logic?
4. How did you monitor and alert on pipeline failures?
5. What was the data volume and frequency you were handling?
""",
            "transformation": """
Tell me about the data transformations you implemented in {context}.

Specifically:
1. Did you use Mapping Data Flows or something else? Why?
2. How did you handle data quality and validation?
3. What transformations were most complex and why?
4. How did you optimize for performance (e.g., partitioning, parallelism)?
"""
        },
        
        "databricks": {
            "optimization": """
You mentioned optimizing Databricks workloads that {metric_claim}.

I want to understand:
1. What type of workload was it (streaming, batch, ML)?
2. What specific optimizations did you apply (partitioning, caching, broadcast joins)?
3. How did you use cluster configuration to improve performance?
4. How did you measure and validate the {metric_claim}?
""",
            "architecture": """
Describe the Databricks architecture you designed for {context}.

Walk me through:
1. How did you organize your notebooks and jobs?
2. What cluster types and sizes did you choose and why?
3. How did you manage Delta Lake tables (partitioning, Z-ordering)?
4. How did you handle security and access control?
"""
        },
        
        "python": {
            "development": """
You mentioned building {context} with Python.

Tell me about:
1. What was the overall architecture/design pattern?
2. How did you structure your code (modules, packages, classes)?
3. What Python features did you leverage (decorators, generators, context managers)?
4. How did you handle error handling and logging?
5. What testing framework did you use and what was your test coverage?
""",
            "optimization": """
Walk me through how you {metric_claim} in your Python project.

Specifically:
1. How did you identify the performance bottleneck?
2. What profiling tools did you use?
3. What specific optimizations did you implement?
4. Did you consider using Cython, numba, or multiprocessing?
"""
        },
        
        "aws": {
            "architecture": """
You mentioned architecting AWS infrastructure for {context}.

Describe your design:
1. What AWS services did you choose and why?
2. How did you design for high availability and fault tolerance?
3. How did you implement security (IAM, VPC, security groups)?
4. What was your cost optimization strategy?
5. How did you handle monitoring and alerting?
""",
            "migration": """
Tell me about the AWS migration you led for {context}.

Walk me through:
1. What was your migration strategy (lift-and-shift, re-platform, refactor)?
2. How did you plan and sequence the migration?
3. What challenges did you encounter and how did you solve them?
4. How did you ensure minimal downtime?
5. How did you achieve the {metric_claim}?
"""
        },
        
        "kubernetes": {
            "deployment": """
You mentioned deploying {context} on Kubernetes.

Describe your approach:
1. How did you structure your Kubernetes manifests (deployments, services, ingress)?
2. What deployment strategy did you use (rolling update, blue-green, canary)?
3. How did you handle configuration management (ConfigMaps, Secrets)?
4. How did you set resource limits and requests?
5. What monitoring and logging solution did you implement?
""",
            "optimization": """
Walk me through how you {metric_claim} with Kubernetes.

Specifically:
1. What was consuming resources before optimization?
2. What K8s features did you leverage (HPA, VPA, cluster autoscaling)?
3. How did you optimize pod resource allocation?
4. How did you validate the cost reduction?
"""
        }
    }
    
    # Enhanced answer guides
    ANSWER_GUIDES = {
        "sql": {
            "concepts": [
                "Query execution plans (EXPLAIN/EXPLAIN ANALYZE)",
                "Index types (B-tree, Hash, GiST, GIN) and when to use each",
                "Query optimizer behavior and statistics",
                "ACID properties and transaction isolation levels",
                "Normalization vs denormalization trade-offs"
            ],
            "tools": [
                "pg_stat_statements or equivalent for query analysis",
                "EXPLAIN ANALYZE for execution plan visualization",
                "Database monitoring tools (pgAdmin, DataGrip, DBeaver)",
                "Profiling tools for slow query identification",
                "Migration tools (Flyway, Liquibase, Alembic)"
            ],
            "techniques": [
                "Index optimization (covering indexes, partial indexes)",
                "Query rewriting (EXISTS vs IN, JOIN strategies)",
                "Partitioning strategies (range, list, hash)",
                "Materialized views for expensive aggregations",
                "Connection pooling and prepared statements"
            ],
            "depth_indicators": [
                "Mentions specific EXPLAIN output columns (cost, rows, width)",
                "Discusses index selectivity and cardinality",
                "References query planner statistics and how to update them",
                "Describes actual performance metrics before/after (not just percentages)",
                "Talks about trade-offs (e.g., index maintenance cost vs query speed)"
            ],
            "red_flags": [
                "Only mentions 'adding indexes' without explaining which type or why",
                "Cannot explain how they measured performance improvement",
                "No mention of EXPLAIN or query plans",
                "Confuses database concepts (e.g., clustered vs non-clustered indexes)",
                "Claims optimization but can't describe the bottleneck"
            ]
        },
        
        "adf": {
            "concepts": [
                "Pipeline orchestration patterns (sequential, parallel, conditional)",
                "Dataset types and linked services",
                "Mapping Data Flow transformation types",
                "Integration Runtime (Azure IR, Self-hosted IR, Azure-SSIS IR)",
                "Activity types (Copy, Data Flow, Stored Procedure, Web)"
            ],
            "tools": [
                "ADF Studio/UI for pipeline design",
                "Azure Monitor and Log Analytics for monitoring",
                "Git integration for CI/CD",
                "Debug mode for testing",
                "Tumbling window triggers vs scheduled triggers"
            ],
            "techniques": [
                "Incremental data loading (watermark, change data capture)",
                "Error handling patterns (try-catch, retry policies)",
                "Parameterization for reusable pipelines",
                "Performance optimization (partition, parallel copy, DIU tuning)",
                "Schema drift handling in Data Flows"
            ],
            "depth_indicators": [
                "Mentions specific DIU (Data Integration Units) tuning",
                "Discusses partitioning strategy for large datasets",
                "References activity dependencies and execution order",
                "Describes monitoring metrics they tracked (duration, data read/written)",
                "Talks about cost optimization (e.g., reducing DIU hours)"
            ],
            "red_flags": [
                "Only mentions 'drag and drop' without understanding what's happening",
                "Cannot explain how error handling works",
                "No mention of monitoring or how they knew pipeline failed",
                "Confuses Data Factory with Databricks or Synapse",
                "Cannot describe how they handled incremental loads"
            ]
        },
        
        "databricks": {
            "concepts": [
                "Delta Lake (ACID transactions, time travel, schema evolution)",
                "Spark optimization (catalyst optimizer, tungsten execution)",
                "Cluster types (standard, high-concurrency, single-node)",
                "Structured Streaming vs batch processing",
                "Unity Catalog for data governance"
            ],
            "tools": [
                "Databricks notebooks (Python, Scala, SQL, R)",
                "Jobs and workflows orchestration",
                "Delta Live Tables for ETL pipelines",
                "MLflow for experiment tracking",
                "Spark UI for performance monitoring"
            ],
            "techniques": [
                "Data partitioning and Z-ordering for query performance",
                "Broadcast joins vs shuffle joins",
                "Caching and persist strategies",
                "Adaptive Query Execution (AQE)",
                "Auto Loader for incremental ingestion"
            ],
            "depth_indicators": [
                "References specific Spark configuration settings",
                "Discusses partitioning columns and rationale",
                "Mentions shuffle operations and how to minimize them",
                "Describes cluster sizing decisions (workers, driver, instance types)",
                "Talks about cost per workload and optimization efforts"
            ],
            "red_flags": [
                "Only knows notebooks, not clusters or jobs",
                "Cannot explain difference between Delta Lake and Parquet",
                "No understanding of Spark execution plans",
                "Claims optimization without mentioning partitioning or caching",
                "Confuses Databricks with generic Spark"
            ]
        }
    }
    
    def __init__(self):
        """Initialize improved question generator."""
        self.matcher = EnhancedSemanticSkillMatcher()
    
    def generate_questions(
        self,
        jd_text: str,
        resume_text: str,
        priority_skills: Optional[List[str]] = None,
        max_questions: int = 10
    ) -> List[InterviewQuestion]:
        """
        Generate improved interview questions.
        
        Returns list of InterviewQuestion objects with detailed guidance.
        """
        # Analyze candidate
        report = self.matcher.analyze_with_priorities(
            jd_text=jd_text,
            resume_text=resume_text,
            priority_skills=priority_skills
        )
        
        questions = []
        
        # Generate questions from validated skills
        for skill_result in report.validated_skills[:max_questions]:
            if not hasattr(skill_result, 'enhanced_evidence') or not skill_result.enhanced_evidence:
                continue
            
            best_evidence = skill_result.enhanced_evidence[0]
            
            # Generate specific question based on skill and evidence
            question = self._generate_specific_question(
                skill_name=skill_result.skill_name,
                evidence=best_evidence,
                experience_depth=getattr(skill_result, 'experience_depth', ExperienceDepth.COMPETENT)
            )
            
            if question:
                questions.append(question)
        
        return questions
    
    def _generate_specific_question(
        self,
        skill_name: str,
        evidence,
        experience_depth: ExperienceDepth
    ) -> Optional[InterviewQuestion]:
        """Generate a specific, well-formatted question."""
        
        evidence_text = evidence.evidence_text
        skill_lower = skill_name.lower()
        
        # Extract metrics if present
        metric_match = None
        has_metrics = getattr(evidence, 'has_metrics', False)
        if has_metrics:
            import re
            # Look for percentage improvements
            metric_match = re.search(r'(\d+)%', evidence_text)
            if not metric_match:
                # Look for other metrics
                metric_match = re.search(r'(reduced|improved|increased).*?by\s+(.+?)(?:\.|,|$)', evidence_text, re.IGNORECASE)
        
        metric_claim = metric_match.group(0) if metric_match else "achieved improvements"
        
        # Extract context (project/system name)
        context = self._extract_context(evidence_text)
        
        # Determine question type based on evidence
        question_type = self._determine_question_type(evidence_text)
        
        # Get skill-specific question template
        question_text = self._get_question_template(
            skill_lower, question_type, context, metric_claim
        )
        
        # Get answer guide
        answer_guide = self._get_answer_guide(skill_lower)
        
        # Generate follow-ups
        follow_ups = self._generate_follow_ups(
            skill_name, evidence_text, has_metrics, question_type
        )
        
        # Create evaluation rubric
        rubric = self._create_evaluation_rubric(skill_name, question_type, evidence_text)
        
        # Determine difficulty
        difficulty = "Advanced" if experience_depth == ExperienceDepth.EXPERT else "Intermediate"
        
        # Determine lifecycle phase
        phase = self._determine_lifecycle_phase(evidence)
        
        return InterviewQuestion(
            lifecycle_phase=phase,
            skill=skill_name,
            question=question_text,
            context_from_resume=evidence_text[:200],
            answer_guide=answer_guide,
            difficulty=difficulty,
            follow_up_questions=follow_ups,
            evaluation_rubric=rubric
        )
    
    def _get_question_template(
        self,
        skill: str,
        question_type: str,
        context: str,
        metric_claim: str
    ) -> str:
        """Get specific question template for skill."""
        
        # Map skill to question template
        for key in self.SKILL_QUESTIONS:
            if key in skill:
                templates = self.SKILL_QUESTIONS[key]
                if question_type in templates:
                    return templates[question_type].format(
                        context=context,
                        metric_claim=metric_claim
                    )
        
        # Generic fallback
        return f"""
Tell me about your work with {skill} on {context}.

Specifically, I want to understand:
1. What was your role and responsibility?
2. What technical approach did you take?
3. What challenges did you face and how did you solve them?
4. How did you measure success? (What metrics did you track?)
5. If you were to do it again, what would you change?
"""
    
    def _get_answer_guide(self, skill: str) -> Dict[str, List[str]]:
        """Get detailed answer guide for skill."""
        
        for key in self.ANSWER_GUIDES:
            if key in skill:
                return self.ANSWER_GUIDES[key]
        
        # Generic guide
        return {
            "concepts": [f"{skill.upper()} fundamentals", "Best practices", "Common patterns"],
            "tools": ["Development tools", "Testing frameworks", "Monitoring solutions"],
            "techniques": ["Problem-solving approaches", "Optimization methods"],
            "depth_indicators": [
                "Provides specific technical details",
                "References actual metrics and outcomes",
                "Discusses trade-offs made",
                "Mentions tools and technologies used"
            ],
            "red_flags": [
                "Vague, generic responses",
                "Cannot explain technical decisions",
                "No mention of metrics or outcomes",
                "Contradicts resume claims"
            ]
        }
    
    def _generate_follow_ups(
        self,
        skill_name: str,
        evidence_text: str,
        has_metrics: bool,
        question_type: str
    ) -> List[str]:
        """Generate targeted follow-up questions."""
        
        follow_ups = []
        
        if has_metrics:
            follow_ups.append(
                f"You mentioned {self._extract_metric(evidence_text)}. "
                "How exactly did you measure that? What tools or methods did you use?"
            )
        
        follow_ups.append(
            f"What was the biggest technical challenge with {skill_name} in this project, "
            "and how did you overcome it?"
        )
        
        follow_ups.append(
            f"If you were to architect this {skill_name} solution today, "
            "what would you do differently based on what you learned?"
        )
        
        if question_type in ["optimization", "migration"]:
            follow_ups.append(
                "Were there any trade-offs or compromises you had to make? "
                "How did you evaluate those trade-offs?"
            )
        
        return follow_ups
    
    def _create_evaluation_rubric(
        self,
        skill_name: str,
        question_type: str,
        evidence_text: str
    ) -> Dict[str, str]:
        """Create clear evaluation criteria."""
        
        return {
            "strong": (
                f"• Provides specific technical details about {skill_name} implementation\n"
                "  • References actual tools, configurations, and approaches used\n"
                "  • Describes measurable outcomes with concrete numbers\n"
                "  • Discusses trade-offs and alternative approaches considered\n"
                "  • Demonstrates deep understanding of underlying concepts"
            ),
            "moderate": (
                f"• Shows general knowledge of {skill_name} but lacks depth\n"
                "  • Mentions some tools/approaches but cannot explain rationale\n"
                "  • Provides metrics but cannot explain measurement methodology\n"
                "  • Answers are somewhat vague or generic\n"
                "  • May need prompting to provide details"
            ),
            "weak": (
                "  • Cannot provide specific examples or details\n"
                "  • Contradicts what's written in resume\n"
                "  • Vague responses with no technical depth\n"
                "  • Cannot explain decisions or trade-offs\n"
                "  • Likely resume padding or exaggeration"
            )
        }
    
    def _extract_context(self, text: str) -> str:
        """Extract project/system context from evidence."""
        # Simple extraction - take first 50 chars or until period
        context = text[:50]
        if '.' in context:
            context = context[:context.index('.')]
        return context.strip()
    
    def _extract_metric(self, text: str) -> str:
        """Extract metric claim from evidence."""
        import re
        metric = re.search(r'(reducing|reduced|improved|increased).*?(\d+%|by\s+\$\d+)', text, re.IGNORECASE)
        if metric:
            return metric.group(0)
        return "the improvement"
    
    def _determine_question_type(self, evidence_text: str) -> str:
        """Determine what type of question to ask based on evidence."""
        text_lower = evidence_text.lower()
        
        if any(word in text_lower for word in ['optimized', 'improved', 'reduced', 'increased']):
            return 'optimization'
        elif any(word in text_lower for word in ['deployed', 'migrated', 'launched']):
            return 'deployment'
        elif any(word in text_lower for word in ['designed', 'architected', 'built']):
            return 'architecture'
        elif any(word in text_lower for word in ['transformed', 'processed', 'ingested']):
            return 'transformation'
        else:
            return 'development'
    
    def _determine_lifecycle_phase(self, evidence) -> LifecyclePhase:
        """Determine lifecycle phase from evidence."""
        evidence_text = evidence.evidence_text.lower()
        
        if any(word in evidence_text for word in ['deployed', 'production', 'live', 'launched']):
            return LifecyclePhase.DEPLOYMENT
        elif any(word in evidence_text for word in ['built', 'implemented', 'developed', 'coded']):
            return LifecyclePhase.DEVELOPMENT
        elif any(word in evidence_text for word in ['designed', 'architected', 'planned']):
            return LifecyclePhase.DESIGN
        elif any(word in evidence_text for word in ['tested', 'quality', 'validated']):
            return LifecyclePhase.TESTING
        else:
            return LifecyclePhase.REQUIREMENTS


if __name__ == "__main__":
    print("Improved Interview Question Generator - Ready")
