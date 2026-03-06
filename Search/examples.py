"""
Example Usage Scripts for Enhanced Recruitment Tool
====================================================

Demonstrates:
1. Security masking workflows
2. Hands-on experience validation
3. Priority skills configuration
4. Batch processing concepts
"""

from security_masker import SecurityMasker
from enhanced_semantic_matcher import EnhancedSemanticSkillMatcher
import json


# ==================== EXAMPLE 1: Security Masking ====================
def example_security_masking():
    """
    Example: Secure resume and JD upload with automatic masking.
    """
    print("=" * 80)
    print("EXAMPLE 1: Security Masking")
    print("=" * 80)
    
    # Sample resume with PII
    resume_with_pii = """
    Jane Smith
    Email: jane.smith@gmail.com
    Phone: +1-555-987-6543
    Address: 456 Oak Avenue, Springfield, IL 62701
    SSN: 987-65-4321
    DOB: 05/20/1988
    
    PROFESSIONAL EXPERIENCE
    
    Senior Python Developer | TechCorp Inc. | 2021-Present
    Email: jane.smith@techcorp.com
    - Led development of microservices platform using Python and FastAPI
    - Optimized PostgreSQL queries, reducing response time by 45%
    - Architected Kubernetes deployment, cutting costs by 30%
    
    Backend Developer | DataStartup | 2019-2021
    - Built REST APIs serving 100K+ daily users
    - Implemented Redis caching layer
    - Collaborated on AWS infrastructure (EC2, S3, Lambda)
    
    SKILLS
    Python, AWS, PostgreSQL, Docker, Kubernetes, FastAPI, Redis
    """
    
    # Sample JD with client-sensitive info
    jd_with_sensitive = """
    Client: Acme Technologies LLC
    Client-ID: CLT-98765
    Project Code: PROJ-ALPHA-2024
    
    CONFIDENTIAL - INTERNAL ONLY
    
    Position: Senior Python Developer
    Budget: $150,000 - $180,000
    
    Our client, a Fortune 500 financial services company, is seeking
    an experienced Python developer for a mission-critical project.
    
    Required Skills:
    - Python (5+ years)
    - AWS (EC2, S3, Lambda, RDS)
    - PostgreSQL
    - Docker & Kubernetes
    - FastAPI or Flask
    - Redis or Memcached
    
    Responsibilities:
    - Design and implement microservices architecture
    - Optimize database performance
    - Lead cloud infrastructure migration
    - Mentor junior developers
    
    Internal Reference: ABC-12345
    """
    
    # Initialize masker
    masker = SecurityMasker()
    
    # Mask resume
    print("\n--- Masking Resume ---")
    resume_result = masker.mask_resume(resume_with_pii)
    print(masker.get_masking_summary(resume_result))
    print("\nMasked Resume Preview (first 500 chars):")
    print(resume_result.masked_text[:500] + "...\n")
    
    # Mask JD
    print("\n--- Masking Job Description ---")
    jd_result = masker.mask_jd(
        jd_with_sensitive,
        known_client_names=["Acme Technologies", "Fortune 500"]
    )
    print(masker.get_masking_summary(jd_result))
    print("\nMasked JD Preview (first 500 chars):")
    print(jd_result.masked_text[:500] + "...\n")
    
    # Export audit log
    from security_masker import create_masking_audit_log
    
    resume_audit = create_masking_audit_log(resume_result, "resume")
    jd_audit = create_masking_audit_log(jd_result, "jd")
    
    print("\n--- Audit Log ---")
    print(json.dumps([resume_audit, jd_audit], indent=2))


# ==================== EXAMPLE 2: Hands-On Experience Validation ====================
def example_hands_on_validation():
    """
    Example: Validate hands-on experience vs. resume padding.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Hands-On Experience Validation")
    print("=" * 80)
    
    jd_text = """
    Senior Python Developer
    
    Required Skills:
    - Python (5+ years hands-on experience)
    - AWS cloud services
    - PostgreSQL database optimization
    - Docker containerization
    - Kubernetes orchestration
    - FastAPI or Django frameworks
    - CI/CD pipelines
    """
    
    # Resume A: Strong hands-on evidence
    resume_strong = """
    PROFESSIONAL EXPERIENCE
    
    Senior Software Engineer | TechCorp | 2021-Present (3 years)
    - Architected and deployed Python microservices platform using FastAPI
      serving 500K+ daily active users with 99.9% uptime
    - Led PostgreSQL optimization initiative, reducing average query time
      from 2.5s to 400ms (84% improvement) through strategic indexing
    - Spearheaded Kubernetes migration of 15 legacy services, cutting
      infrastructure costs by $180K annually (30% reduction)
    - Built CI/CD pipelines with GitHub Actions, reducing deployment time
      from 2 hours to 15 minutes
    - Mentored team of 4 junior developers on AWS best practices
    
    Backend Developer | StartupX | 2019-2021 (2 years)
    - Developed and deployed REST APIs using Django for customer analytics
    - Implemented Redis caching layer, improving response time by 60%
    - Worked with AWS services: EC2, S3, Lambda, RDS, CloudWatch
    - Containerized applications using Docker, established CI/CD pipeline
    
    SKILLS
    Python, FastAPI, Django, Flask, AWS, PostgreSQL, Redis, Docker,
    Kubernetes, Jenkins, GitHub Actions, Git, Linux
    """
    
    # Resume B: Weak hands-on evidence (resume padding)
    resume_weak = """
    PROFESSIONAL EXPERIENCE
    
    Software Developer | Various Companies | 2019-Present
    - Worked on various projects using different technologies
    - Participated in team meetings and code reviews
    - Contributed to software development lifecycle
    - Assisted with bug fixes and feature implementations
    - Familiar with cloud technologies and modern frameworks
    
    SKILLS
    Python, Java, JavaScript, C++, Ruby, Go, Rust
    AWS, Azure, GCP, DigitalOcean
    PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch
    Docker, Kubernetes, Terraform, Ansible
    FastAPI, Django, Flask, React, Angular, Vue
    Jenkins, CircleCI, GitHub Actions, GitLab CI
    """
    
    # Initialize matcher
    matcher = EnhancedSemanticSkillMatcher()
    
    # Analyze Resume A (Strong)
    print("\n--- Analyzing Resume A (Strong Hands-On Evidence) ---")
    report_strong = matcher.analyze_with_priorities(
        jd_text=jd_text,
        resume_text=resume_strong,
        priority_skills=["Python", "AWS", "Kubernetes", "PostgreSQL"]
    )
    
    print(f"\nOverall Fit Score: {report_strong.overall_relevance_score:.0%}")
    print(f"Validated Skills: {len(report_strong.validated_skills)}")
    print(f"Weak Evidence: {len(report_strong.weak_skills)}")
    print(f"Missing Skills: {len(report_strong.missing_skills)}")
    
    print("\nTop Validated Skills:")
    for skill in report_strong.validated_skills[:5]:
        priority = "🎯" if skill.priority_skill else ""
        print(f"  {priority} {skill.skill_name}: {skill.hands_on_score:.0%} hands-on")
        if hasattr(skill, 'experience_depth'):
            print(f"    Depth: {skill.experience_depth.value}")
        print(f"    {skill.reasoning[:100]}...")
    
    # Analyze Resume B (Weak)
    print("\n--- Analyzing Resume B (Weak/Padding Evidence) ---")
    report_weak = matcher.analyze_with_priorities(
        jd_text=jd_text,
        resume_text=resume_weak,
        priority_skills=["Python", "AWS", "Kubernetes", "PostgreSQL"]
    )
    
    print(f"\nOverall Fit Score: {report_weak.overall_relevance_score:.0%}")
    print(f"Validated Skills: {len(report_weak.validated_skills)}")
    print(f"Weak Evidence: {len(report_weak.weak_skills)}")
    print(f"Ignored (Skills-only): {len(report_weak.ignored_skills)}")
    
    print("\nIgnored Skills (No Hands-On Evidence):")
    for skill in report_weak.ignored_skills[:5]:
        print(f"  ⊘ {skill.skill_name}")
        print(f"    {skill.reasoning[:100]}...")
    
    # Compare
    print("\n--- Comparison ---")
    print(f"Resume A (Strong): {report_strong.overall_relevance_score:.0%} fit")
    print(f"Resume B (Weak):   {report_weak.overall_relevance_score:.0%} fit")
    print(f"\nDifference: {(report_strong.overall_relevance_score - report_weak.overall_relevance_score) * 100:.0f} percentage points")


# ==================== EXAMPLE 3: Priority Skills Configuration ====================
def example_priority_skills():
    """
    Example: Configure priority skills for targeted evaluation.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Priority Skills Configuration")
    print("=" * 80)
    
    jd_text = """
    DevOps Engineer Position
    
    MUST-HAVE Skills (Critical):
    - Kubernetes (production experience)
    - Terraform (infrastructure as code)
    - AWS (cloud architecture)
    
    NICE-TO-HAVE Skills:
    - Python scripting
    - Docker
    - Jenkins CI/CD
    - Monitoring tools (Prometheus, Grafana)
    """
    
    resume_text = """
    PROFESSIONAL EXPERIENCE
    
    DevOps Engineer | CloudCorp | 2022-Present
    - Architected and managed Kubernetes clusters for 20+ microservices
      in production, handling 1M+ daily requests
    - Built Terraform modules for AWS infrastructure provisioning,
      reducing setup time from 2 weeks to 2 days
    - Led AWS migration project, cutting monthly costs by $50K
    - Developed Python automation scripts for deployment workflows
    
    Systems Administrator | LegacyCorp | 2020-2022
    - Managed on-premise servers and networking
    - Worked with Docker for containerization
    - Set up basic Jenkins pipelines
    - Installed monitoring tools (Prometheus, Grafana)
    
    SKILLS
    Kubernetes, Terraform, AWS, Python, Docker, Jenkins,
    Prometheus, Grafana, Ansible, Git, Linux
    """
    
    matcher = EnhancedSemanticSkillMatcher()
    
    # Analyze WITH priority skills configured
    print("\n--- Analysis WITH Priority Skills (Kubernetes, Terraform, AWS) ---")
    report_priority = matcher.analyze_with_priorities(
        jd_text=jd_text,
        resume_text=resume_text,
        priority_skills=["Kubernetes", "Terraform", "AWS"]
    )
    
    print(f"\nOverall Fit Score: {report_priority.overall_relevance_score:.0%}")
    
    print("\nPriority Skills Status:")
    for skill in report_priority.validated_skills:
        if skill.priority_skill:
            print(f"  🎯 {skill.skill_name}: {skill.hands_on_score:.0%} hands-on")
            print(f"     Depth: {skill.experience_depth.value if hasattr(skill, 'experience_depth') else 'N/A'}")
    
    print("\nRecommendations:")
    for rec in report_priority.recommendations:
        print(f"  • {rec}")
    
    # Analyze WITHOUT priority skills (for comparison)
    print("\n--- Analysis WITHOUT Priority Skills ---")
    report_no_priority = matcher.analyze_with_priorities(
        jd_text=jd_text,
        resume_text=resume_text,
        priority_skills=[]  # No priorities
    )
    
    print(f"\nOverall Fit Score: {report_no_priority.overall_relevance_score:.0%}")
    print("\n(Notice the scoring difference when priorities are configured)")


# ==================== EXAMPLE 4: Batch Processing Concept ====================
def example_batch_processing_concept():
    """
    Example: Concept for batch processing multiple candidates.
    (This is a demonstration of how batch processing would work)
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Batch Processing Concept")
    print("=" * 80)
    
    jd_text = """
    Senior Data Engineer
    
    Required Skills:
    - Python (advanced)
    - SQL (expert level)
    - Apache Spark
    - AWS (S3, EMR, Redshift)
    - Data pipeline design
    """
    
    # Simulated candidate resumes
    candidates = {
        "Candidate_A": """
        Senior Data Engineer with 5 years experience.
        Led Spark pipeline development processing 10TB daily data.
        Optimized SQL queries on Redshift, improving performance by 60%.
        Built AWS data lakes using S3 and EMR.
        Python expert with data engineering focus.
        """,
        
        "Candidate_B": """
        Data Analyst with 3 years experience.
        Worked with SQL for reporting and analytics.
        Used Python for data analysis and visualization.
        Basic familiarity with Spark and AWS.
        """,
        
        "Candidate_C": """
        Software Engineer with data interests.
        Python developer with web development focus.
        Some SQL experience for application databases.
        Skills: Python, SQL, React, Node.js, AWS, Spark
        """,
    }
    
    matcher = EnhancedSemanticSkillMatcher()
    
    print("\n--- Batch Processing Results ---")
    results = []
    
    for candidate_id, resume_text in candidates.items():
        report = matcher.analyze_with_priorities(
            jd_text=jd_text,
            resume_text=resume_text,
            priority_skills=["Python", "SQL", "Apache Spark", "AWS"]
        )
        
        results.append({
            "candidate_id": candidate_id,
            "fit_score": report.overall_relevance_score,
            "validated_skills": len(report.validated_skills),
            "priority_skills_validated": sum(
                1 for s in report.validated_skills if s.priority_skill
            ),
            "expert_skills": sum(
                1 for s in report.validated_skills
                if hasattr(s, 'experience_depth') and s.experience_depth.name == 'EXPERT'
            )
        })
    
    # Sort by fit score
    results.sort(key=lambda x: x['fit_score'], reverse=True)
    
    print("\nRanked Candidates:\n")
    print(f"{'Rank':<6} {'Candidate':<15} {'Fit Score':<12} {'Validated':<12} {'Priority':<12} {'Expert':<10}")
    print("-" * 80)
    
    for rank, result in enumerate(results, 1):
        print(f"{rank:<6} {result['candidate_id']:<15} "
              f"{result['fit_score']:<12.0%} "
              f"{result['validated_skills']:<12} "
              f"{result['priority_skills_validated']:<12} "
              f"{result['expert_skills']:<10}")
    
    print("\nRecommendation:")
    top_candidate = results[0]
    if top_candidate['fit_score'] >= 0.75:
        print(f"✅ Strong match found: {top_candidate['candidate_id']} ({top_candidate['fit_score']:.0%} fit)")
        print("   Recommend moving to interview stage.")
    elif top_candidate['fit_score'] >= 0.60:
        print(f"⚠️  Moderate match: {top_candidate['candidate_id']} ({top_candidate['fit_score']:.0%} fit)")
        print("   Recommend phone screen to assess depth.")
    else:
        print(f"❌ No strong candidates in this batch (top: {top_candidate['fit_score']:.0%})")
        print("   Recommend expanding search criteria or sourcing more candidates.")


# ==================== MAIN ====================
def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ENHANCED RECRUITMENT TOOL - EXAMPLE USAGE")
    print("=" * 80)
    
    example_security_masking()
    example_hands_on_validation()
    example_priority_skills()
    example_batch_processing_concept()
    
    print("\n" + "=" * 80)
    print("Examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
