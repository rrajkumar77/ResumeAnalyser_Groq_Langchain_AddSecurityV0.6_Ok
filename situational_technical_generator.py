"""
Situational Technical Interview Questions Generator
===================================================

Generates scenario-based technical questions to assess:
- Problem-solving approach
- System design thinking
- Troubleshooting skills
- Trade-off analysis
- Real-world technical judgment

These are "What would you do if..." questions based on JD requirements.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class ScenarioType(Enum):
    """Types of situational scenarios."""
    SYSTEM_DESIGN = "System Design"
    TROUBLESHOOTING = "Troubleshooting"
    OPTIMIZATION = "Performance Optimization"
    SCALABILITY = "Scalability Challenge"
    TRADE_OFF = "Trade-off Decision"
    PRODUCTION_INCIDENT = "Production Incident"
    ARCHITECTURE = "Architecture Decision"


@dataclass
class SituationalQuestion:
    """Situational technical question with scenario."""
    scenario_type: ScenarioType
    skill_area: str
    scenario: str
    question: str
    ideal_approach: List[str]
    key_considerations: List[str]
    red_flags: List[str]
    follow_up_questions: List[str]
    difficulty: str
    
    def format_for_interviewer(self) -> str:
        """Format question for display."""
        output = f"""
{'='*80}
📌 SCENARIO TYPE: {self.scenario_type.value}
SKILL AREA: {self.skill_area} | DIFFICULTY: {self.difficulty}
{'='*80}

🎬 SCENARIO:
{self.scenario}

❓ QUESTION:
{self.question}

{'─'*80}
✅ IDEAL APPROACH (What you want to hear):

{chr(10).join(f'  {i+1}. {step}' for i, step in enumerate(self.ideal_approach))}

{'─'*80}
🔑 KEY CONSIDERATIONS (Should mention):

{chr(10).join(f'  • {consideration}' for consideration in self.key_considerations)}

{'─'*80}
🚩 RED FLAGS (Warning signs):

{chr(10).join(f'  ⚠️  {flag}' for flag in self.red_flags)}

{'─'*80}
🔍 FOLLOW-UP QUESTIONS:

{chr(10).join(f'  {i+1}. {q}' for i, q in enumerate(self.follow_up_questions))}

{'='*80}
"""
        return output


class SituationalTechnicalGenerator:
    """
    Generates situational technical interview questions based on JD.
    """
    
    # Scenario templates by skill area
    SCENARIOS = {
        "sql": {
            "troubleshooting": {
                "scenario": """
Your production database is experiencing severe performance degradation. 
Users are reporting that queries that normally take 2-3 seconds are now 
taking 30+ seconds. The application is timing out, and customers are 
complaining. This started happening after yesterday's deployment.

Database metrics show:
- CPU: 95% utilization (normally 40%)
- Active connections: 180 (normally 50)
- Slow query log shows several queries taking 30+ seconds
- No recent schema changes
- Table sizes haven't changed significantly
""",
                "question": "Walk me through your troubleshooting process. What would you do first, second, third? How would you identify the root cause?",
                "ideal_approach": [
                    "Check what changed in yesterday's deployment (code, queries, indexes)",
                    "Identify the slow queries using pg_stat_statements or slow query log",
                    "Run EXPLAIN ANALYZE on the slow queries to see execution plans",
                    "Check if query plans changed (missing indexes, wrong join order)",
                    "Look for lock contention using pg_locks",
                    "Check if statistics are stale (needs ANALYZE)",
                    "Implement quick fix (add missing index, revert bad query)",
                    "Set up monitoring to prevent recurrence"
                ],
                "key_considerations": [
                    "Systematic approach (gather data before making changes)",
                    "Check monitoring/metrics first",
                    "Consider recent changes as likely culprit",
                    "Balance quick fix vs root cause analysis",
                    "Communication with stakeholders about timeline"
                ],
                "red_flags": [
                    "Randomly tries solutions without investigation",
                    "Doesn't check what changed recently",
                    "No mention of EXPLAIN or query plans",
                    "Suggests restarting database as first step",
                    "Doesn't consider impact of changes on production"
                ]
            },
            "optimization": {
                "scenario": """
You need to optimize a reporting query that joins 5 tables and aggregates 
data across 10 million rows. Current execution time is 45 seconds, and the 
business needs it under 5 seconds. The query runs hourly during business hours.

Current query structure:
- SELECT with aggregations (SUM, COUNT, AVG)
- 5 table JOINs (orders, customers, products, categories, regions)
- WHERE clause filtering last 30 days
- GROUP BY multiple columns
- ORDER BY aggregated column
""",
                "question": "How would you approach optimizing this query? What's your systematic process?",
                "ideal_approach": [
                    "Run EXPLAIN ANALYZE to understand current execution plan",
                    "Identify the most expensive operations (sequential scans, sorts)",
                    "Add appropriate indexes (covering indexes if possible)",
                    "Consider partitioning the orders table by date",
                    "Evaluate if denormalization or materialized view makes sense",
                    "Test optimization on copy of production data",
                    "Measure improvement and validate results match",
                    "Deploy during low-traffic window"
                ],
                "key_considerations": [
                    "Measure before and after (EXPLAIN ANALYZE)",
                    "Index maintenance cost vs query performance gain",
                    "Disk space for indexes/materialized views",
                    "Whether data can be pre-aggregated",
                    "Impact on write performance if adding indexes"
                ],
                "red_flags": [
                    "Just says 'add indexes' without analyzing which ones",
                    "Doesn't mention measuring current performance",
                    "Ignores trade-offs (index maintenance, disk space)",
                    "Suggests caching without considering data freshness",
                    "No validation that results remain correct"
                ]
            }
        },
        
        "python": {
            "system_design": {
                "scenario": """
You need to build a Python service that processes uploaded CSV files 
(1-10GB each) and loads them into a database. Files are uploaded by users 
throughout the day. Requirements:
- Process files asynchronously (don't block upload)
- Validate data quality (reject bad rows, log issues)
- Handle 100+ concurrent uploads
- Provide progress updates to users
- Retry failed uploads
- Scale to 1000s of files per day
""",
                "question": "Design the architecture for this system. What components would you use and why?",
                "ideal_approach": [
                    "Upload endpoint stores file in S3/blob storage, returns job ID",
                    "Queue system (Celery, RQ, or SQS) for async processing",
                    "Worker pool to process files in parallel",
                    "Chunk large files to avoid memory issues (pandas chunks, csv reader)",
                    "Database for job tracking (status, progress, errors)",
                    "WebSocket or polling endpoint for progress updates",
                    "Dead letter queue for failed jobs",
                    "Monitoring and alerting for failed jobs"
                ],
                "key_considerations": [
                    "Memory management (streaming vs loading entire file)",
                    "Error handling (partial failures, retries)",
                    "Idempotency (handle duplicate uploads)",
                    "Scalability (horizontal scaling of workers)",
                    "Monitoring (job queue depth, processing time)",
                    "Data validation strategy (fail fast vs log and continue)"
                ],
                "red_flags": [
                    "Suggests synchronous processing (blocks upload)",
                    "No consideration for memory with large files",
                    "Loads entire 10GB file into memory",
                    "No error handling or retry mechanism",
                    "No progress tracking for users",
                    "Single-threaded solution for 100+ concurrent uploads"
                ]
            },
            "production_incident": {
                "scenario": """
Your Python API is running in production (Kubernetes) and suddenly starts 
returning 500 errors for 30% of requests. The other 70% work fine. 
Logs show: 'ConnectionPoolTimeoutError: Pool reached maximum size and no 
more connections are allowed.'

Current setup:
- Flask API with SQLAlchemy ORM
- PostgreSQL database
- Deployed in Kubernetes (5 pods)
- Normal traffic load (not a spike)
- Started happening 2 hours ago
""",
                "question": "How do you diagnose and fix this issue?",
                "ideal_approach": [
                    "Check database connection pool settings (max_connections, pool_size)",
                    "Look for connection leaks (not closing connections properly)",
                    "Check if a recent deployment changed connection handling",
                    "Monitor active database connections (pg_stat_activity)",
                    "Review code for missing connection.close() or session.close()",
                    "Quick fix: Increase connection pool size temporarily",
                    "Root cause: Fix connection leaks in code",
                    "Add connection pool monitoring to prevent recurrence"
                ],
                "key_considerations": [
                    "Impact: 30% errors means immediate action needed",
                    "Balance quick fix vs proper fix",
                    "Why only 30%? (some requests don't hit DB?)",
                    "Communication: update stakeholders on timeline",
                    "Prevention: connection pool monitoring"
                ],
                "red_flags": [
                    "Suggests restarting pods without investigation",
                    "Doesn't understand connection pooling",
                    "No mention of checking for connection leaks",
                    "Just increases pool size without finding root cause",
                    "Doesn't consider impact on database"
                ]
            }
        },
        
        "aws": {
            "architecture": {
                "scenario": """
You're tasked with migrating a monolithic application to AWS. Current setup:
- Monolithic Python application (single server)
- PostgreSQL database (1TB data)
- File uploads stored on local disk (500GB)
- 10,000 daily active users
- Peak traffic: 500 concurrent users
- Needs 99.9% uptime SLA

Business wants:
- High availability (multi-AZ)
- Auto-scaling during traffic spikes
- Cost-effective solution
- Minimal changes to application code
""",
                "question": "Design the AWS architecture for this migration. What services would you use and why?",
                "ideal_approach": [
                    "Application: ECS/EKS or EC2 with Auto Scaling Group across multiple AZs",
                    "Load balancer: Application Load Balancer for traffic distribution",
                    "Database: RDS PostgreSQL with Multi-AZ for high availability",
                    "File storage: S3 for uploads (durable, scalable, cost-effective)",
                    "Caching: ElastiCache (Redis) for session/data caching",
                    "CDN: CloudFront for static assets",
                    "Monitoring: CloudWatch for metrics and alarms",
                    "Backup: RDS automated backups + S3 versioning"
                ],
                "key_considerations": [
                    "Database migration strategy (DMS, pg_dump, blue-green)",
                    "File migration to S3 (batch upload, update app to use S3)",
                    "Network design (VPC, subnets, security groups)",
                    "Cost optimization (Reserved Instances, S3 storage classes)",
                    "Disaster recovery and backup strategy",
                    "Monitoring and alerting setup"
                ],
                "red_flags": [
                    "Single AZ deployment (doesn't meet HA requirement)",
                    "No load balancing or auto-scaling",
                    "Suggests EC2 without considering managed services",
                    "No plan for database migration",
                    "Ignores cost considerations",
                    "No monitoring or backup strategy"
                ]
            },
            "troubleshooting": {
                "scenario": """
Your Lambda function (Python 3.11) that processes S3 uploads is timing out 
after 1 minute (max timeout). It's supposed to:
1. Download CSV from S3
2. Process/transform data
3. Upload to database
4. Send confirmation email

Logs show it times out during step 2 (processing). File sizes vary from 
10MB to 500MB. Smaller files process fine, larger ones timeout.

Lambda config:
- Memory: 512MB
- Timeout: 60s (max for your use case)
- Trigger: S3 upload event
""",
                "question": "How would you solve this? What are your options?",
                "ideal_approach": [
                    "Analyze: Lambda not suited for long-running tasks (15min max)",
                    "Option 1: Move to ECS/Fargate for longer tasks",
                    "Option 2: Split processing (Lambda triggers Step Functions)",
                    "Option 3: Process in chunks with multiple Lambda invocations",
                    "Option 4: Use Lambda to queue job, process in ECS worker",
                    "Recommend: Option 4 - Lambda → SQS → ECS worker",
                    "Benefits: Scalable, cost-effective, no Lambda timeout limits"
                ],
                "key_considerations": [
                    "Lambda limitations (15min max, memory constraints)",
                    "Cost comparison (Lambda vs ECS for long tasks)",
                    "Processing time vs file size relationship",
                    "Error handling and retries",
                    "Monitoring and alerting for failures"
                ],
                "red_flags": [
                    "Suggests increasing Lambda memory (doesn't solve timeout)",
                    "Doesn't recognize Lambda isn't right tool for this",
                    "No consideration of cost for large files",
                    "Processes entire file in memory (500MB in 512MB Lambda)",
                    "No alternative architecture proposed"
                ]
            }
        },
        
        "kubernetes": {
            "scalability": {
                "scenario": """
Your microservices application on Kubernetes is experiencing issues during 
traffic spikes (Black Friday, etc.). Symptoms:
- Pods are getting OOMKilled (out of memory)
- Response times spike to 10+ seconds
- Some requests return 503 Service Unavailable
- After spike, some pods never recover and stay in CrashLoopBackOff

Current setup:
- Deployment with 5 replicas
- CPU: request 100m, limit 500m
- Memory: request 256Mi, limit 512Mi
- No HPA (Horizontal Pod Autoscaler) configured
- No PDB (Pod Disruption Budget)
""",
                "question": "How would you redesign this to handle traffic spikes better?",
                "ideal_approach": [
                    "Implement HPA based on CPU/memory metrics",
                    "Set proper resource requests and limits (profile actual usage)",
                    "Add readiness and liveness probes",
                    "Implement PDB to ensure minimum availability during updates",
                    "Add resource quotas and limit ranges at namespace level",
                    "Consider Vertical Pod Autoscaler for right-sizing",
                    "Implement circuit breakers for graceful degradation",
                    "Set up monitoring and alerts for resource usage"
                ],
                "key_considerations": [
                    "Resource requests vs limits (guaranteed vs max)",
                    "HPA metrics (CPU, memory, custom metrics)",
                    "Scale-up and scale-down thresholds",
                    "Pod startup time vs spike arrival speed",
                    "Cost implications of over-provisioning",
                    "Cluster capacity and node scaling"
                ],
                "red_flags": [
                    "Just increases memory limits without investigation",
                    "Doesn't understand difference between requests and limits",
                    "No mention of HPA or auto-scaling",
                    "Suggests very high limits (wasteful)",
                    "No consideration for graceful degradation",
                    "Doesn't mention monitoring resource usage"
                ]
            }
        },
        
        "databricks": {
            "optimization": {
                "scenario": """
Your Databricks job that processes daily data takes 6 hours to complete, 
but business needs it to finish in under 2 hours (before market open). 
Current setup:
- Reads 500GB of raw Parquet files from S3
- Performs complex transformations and joins
- Writes to Delta Lake table (partitioned by date)
- Uses standard cluster (4 workers, 16 cores each)
- Job is scheduled daily at midnight

Spark UI shows:
- 80% of time spent in shuffle operations
- Many small tasks (10,000+ tasks)
- Some stages have data skew
""",
                "question": "How would you optimize this to meet the 2-hour requirement?",
                "ideal_approach": [
                    "Analyze Spark UI to identify bottlenecks (shuffle, skew, small files)",
                    "Optimize partitioning of input data (repartition before shuffle)",
                    "Use broadcast joins for small tables",
                    "Address data skew (salt keys, split skewed data)",
                    "Increase cluster size or use high-concurrency cluster",
                    "Enable Adaptive Query Execution (AQE)",
                    "Optimize Delta Lake writes (optimize file size, Z-order)",
                    "Consider caching intermediate results if reused"
                ],
                "key_considerations": [
                    "Cost vs performance trade-off (bigger cluster = more cost)",
                    "Data skew impact (one task takes 10x longer)",
                    "Shuffle operations are expensive (minimize data movement)",
                    "Small file problem (many small tasks = overhead)",
                    "Partitioning strategy affects read/write performance",
                    "AQE can automatically handle some optimizations"
                ],
                "red_flags": [
                    "Just says 'add more workers' without analysis",
                    "Doesn't understand shuffle operations",
                    "No mention of Spark UI or profiling",
                    "Ignores data skew issues",
                    "Doesn't consider cost implications",
                    "No systematic approach to optimization"
                ]
            }
        }
    }
    
    def generate_situational_questions(
        self,
        jd_text: str,
        num_questions: int = 8
    ) -> List[SituationalQuestion]:
        """
        Generate situational technical questions based on JD.
        
        Args:
            jd_text: Job description text
            num_questions: Number of questions to generate
            
        Returns:
            List of SituationalQuestion objects
        """
        # Extract required skills from JD
        skills = self._extract_skills_from_jd(jd_text)
        
        questions = []
        
        # Generate questions for each skill found
        for skill in skills[:num_questions]:
            skill_lower = skill.lower()
            
            # Find matching scenario template
            for template_skill in self.SCENARIOS:
                if template_skill in skill_lower:
                    # Get all scenario types for this skill
                    scenarios = self.SCENARIOS[template_skill]
                    
                    # Pick a scenario type
                    for scenario_type_key, scenario_data in scenarios.items():
                        question = self._create_situational_question(
                            skill=skill,
                            scenario_type_key=scenario_type_key,
                            scenario_data=scenario_data
                        )
                        questions.append(question)
                        
                        if len(questions) >= num_questions:
                            return questions
        
        # If we don't have enough questions, add generic ones
        while len(questions) < num_questions:
            questions.append(self._create_generic_question(
                skill=skills[len(questions) % len(skills)] if skills else "General"
            ))
        
        return questions[:num_questions]
    
    def _create_situational_question(
        self,
        skill: str,
        scenario_type_key: str,
        scenario_data: Dict
    ) -> SituationalQuestion:
        """Create a situational question from template."""
        
        scenario_type_map = {
            "troubleshooting": ScenarioType.TROUBLESHOOTING,
            "optimization": ScenarioType.OPTIMIZATION,
            "system_design": ScenarioType.SYSTEM_DESIGN,
            "architecture": ScenarioType.ARCHITECTURE,
            "scalability": ScenarioType.SCALABILITY,
            "production_incident": ScenarioType.PRODUCTION_INCIDENT,
        }
        
        # Generate follow-up questions
        follow_ups = [
            "What metrics would you monitor to prevent this in the future?",
            "How would you communicate the issue and timeline to stakeholders?",
            "What documentation would you create after resolving this?"
        ]
        
        return SituationalQuestion(
            scenario_type=scenario_type_map.get(scenario_type_key, ScenarioType.TROUBLESHOOTING),
            skill_area=skill,
            scenario=scenario_data["scenario"].strip(),
            question=scenario_data["question"],
            ideal_approach=scenario_data["ideal_approach"],
            key_considerations=scenario_data["key_considerations"],
            red_flags=scenario_data["red_flags"],
            follow_up_questions=follow_ups,
            difficulty="Senior"
        )
    
    def _create_generic_question(self, skill: str) -> SituationalQuestion:
        """Create a generic situational question."""
        return SituationalQuestion(
            scenario_type=ScenarioType.TRADE_OFF,
            skill_area=skill,
            scenario=f"You need to make a technical decision about {skill} implementation.",
            question=f"How would you approach this {skill} decision?",
            ideal_approach=["Systematic analysis", "Consider trade-offs", "Document decision"],
            key_considerations=["Performance", "Cost", "Maintainability"],
            red_flags=["No systematic approach", "Ignores trade-offs"],
            follow_up_questions=["What would you do differently?"],
            difficulty="Mid-Senior"
        )
    
    def _extract_skills_from_jd(self, jd_text: str) -> List[str]:
        """Extract technical skills from JD."""
        # Simple keyword extraction
        skills = []
        skill_keywords = [
            "SQL", "PostgreSQL", "MySQL", "Python", "AWS", "Azure", "GCP",
            "Kubernetes", "K8s", "Docker", "Databricks", "Spark", "ADF",
            "Data Factory", "ETL", "API", "REST", "Lambda", "EC2", "S3"
        ]
        
        jd_lower = jd_text.lower()
        for keyword in skill_keywords:
            if keyword.lower() in jd_lower:
                skills.append(keyword)
        
        return skills if skills else ["General"]


if __name__ == "__main__":
    print("Situational Technical Question Generator - Ready")
