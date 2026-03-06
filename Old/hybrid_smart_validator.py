"""
Hybrid Smart Validator - LLM + Regex Fallback
==============================================

Features:
1. Uses LLM only for JD parsing (1 call instead of 15+)
2. Falls back to regex if rate limit hit
3. Caches results to avoid repeat calls
4. Better error handling
"""

import os
import json
import re
import time
from typing import List, Dict, Optional
from groq import Groq

from semantic_validator_optimized import (
    EnhancedResumeValidator,
    JDSummary,
    SkillPriority,
    JDSkill
)


class HybridSmartValidator(EnhancedResumeValidator):
    """
    Smart hybrid validator that:
    - Uses LLM only for JD parsing (saves tokens)
    - Uses regex for skill validation (faster)
    - Falls back gracefully on errors
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.use_llm = bool(self.api_key)
        self.jd_cache = {}  # Cache parsed JDs
        
        if self.use_llm:
            try:
                self.client = Groq(api_key=self.api_key)
                self.model = "llama-3.3-70b-versatile"
            except Exception as e:
                print(f"⚠️ LLM init failed: {e}")
                self.use_llm = False
    
    def validate_candidate(self, jd_text: str, resume_text: str, candidate_name: str = "Candidate"):
        """Override to use hybrid approach"""
        
        # Step 1: Parse JD (try LLM first, fallback to regex)
        jd_summary = self._parse_jd_smart(jd_text)
        
        # If JD parsing failed completely, return basic report
        if not jd_summary.mandatory_skills and not jd_summary.highly_desired_skills:
            print("⚠️ JD parsing returned no skills, using manual extraction...")
            jd_summary = self._manual_jd_extraction(jd_text)
        
        # Step 2: Use regex-based validation (fast, no API calls)
        # This is handled by parent class
        return super().validate_candidate(jd_text, resume_text, candidate_name)
    
    def _parse_jd_smart(self, jd_text: str) -> JDSummary:
        """Smart JD parsing with LLM + fallback"""
        
        # Check cache first
        jd_hash = hash(jd_text[:1000])
        if jd_hash in self.jd_cache:
            print("📦 Using cached JD analysis")
            return self.jd_cache[jd_hash]
        
        # Try LLM if available
        if self.use_llm:
            try:
                print("🤖 Parsing JD with LLM...")
                summary = self._llm_parse_jd(jd_text)
                
                # Cache result
                self.jd_cache[jd_hash] = summary
                return summary
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if rate limit
                if 'rate_limit' in error_msg.lower() or '429' in error_msg:
                    print("⚠️ Rate limit hit, switching to regex mode for this session")
                    self.use_llm = False  # Disable for rest of session
                else:
                    print(f"⚠️ LLM parsing error: {error_msg[:100]}")
        
        # Fallback to regex
        print("📝 Using regex-based JD parsing...")
        summary = self.jd_analyzer.analyze_jd(jd_text)
        
        # Cache result
        self.jd_cache[jd_hash] = summary
        return summary
    
    def _llm_parse_jd(self, jd_text: str) -> JDSummary:
        """Parse JD using LLM"""
        
        prompt = f"""Analyze this job description and extract ONLY the key information.

JOB DESCRIPTION:
{jd_text[:3000]}

Extract and return as JSON:
{{
  "role_title": "Job title",
  "role_archetype": "Product Manager/Engineer/Data Scientist/etc",
  "core_problem": "Main challenge (1-2 sentences)",
  "mandatory_skills": ["skill1", "skill2", "skill3"],
  "highly_desired_skills": ["skill4", "skill5"],
  "good_to_have_skills": ["skill6"],
  "excluded_skills": ["skill7"],
  "required_experience_years": 5,
  "domain_requirements": ["pharma", "healthcare"]
}}

CRITICAL RULES:
- Keep skills as complete phrases (e.g., "RAG architecture" not just "RAG")
- Extract 5-10 mandatory skills MAX
- Extract 3-5 excluded skills MAX
- NO fragments, NO connecting words
- Focus on technical/business skills only

Return ONLY the JSON, no markdown:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000  # Reduced to save tokens
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean JSON
        if "```json" in result_text:
            result_text = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
        elif "```" in result_text:
            result_text = re.search(r'```\s*(.*?)\s*```', result_text, re.DOTALL).group(1)
        
        data = json.loads(result_text)
        
        # Convert to JDSummary
        summary = JDSummary(
            role_title=data.get("role_title", "Position"),
            role_archetype=data.get("role_archetype", "General"),
            core_problem=data.get("core_problem", "See JD for details"),
            required_experience_years=data.get("required_experience_years"),
            domain_requirements=data.get("domain_requirements", [])
        )
        
        # Convert skills
        for skill_name in data.get("mandatory_skills", [])[:10]:  # Limit
            if skill_name and len(skill_name) > 2:
                summary.mandatory_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.MANDATORY,
                    keywords=self._generate_keywords(skill_name),
                    context="Mandatory"
                ))
        
        for skill_name in data.get("highly_desired_skills", [])[:5]:
            if skill_name and len(skill_name) > 2:
                summary.highly_desired_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.HIGHLY_DESIRED,
                    keywords=self._generate_keywords(skill_name),
                    context="Highly Desired"
                ))
        
        for skill_name in data.get("good_to_have_skills", [])[:5]:
            if skill_name and len(skill_name) > 2:
                summary.good_to_have_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.GOOD_TO_HAVE,
                    keywords=self._generate_keywords(skill_name),
                    context="Good-to-Have"
                ))
        
        for skill_name in data.get("excluded_skills", [])[:5]:
            if skill_name and len(skill_name) > 2:
                summary.excluded_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.EXCLUDED,
                    keywords=self._generate_keywords(skill_name),
                    context="Excluded"
                ))
        
        # Generate search keywords
        summary.search_keywords = [kw for skill in summary.mandatory_skills[:5] for kw in skill.keywords[:2]]
        summary.reject_keywords = [kw for skill in summary.excluded_skills[:3] for kw in skill.keywords[:2]]
        
        return summary
    
    def _manual_jd_extraction(self, jd_text: str) -> JDSummary:
        """Manual extraction for known JD formats (like Indegene)"""
        
        summary = JDSummary(
            role_title="GenAI Product/Program Lead",
            role_archetype="Product Manager",
            core_problem="Translate pharma use-cases into build-ready requirements and drive GenAI adoption"
        )
        
        # Check if it's the Indegene JD format
        if "genai" in jd_text.lower() and "product" in jd_text.lower() and "life sciences" in jd_text.lower():
            # Manually define skills for this specific JD
            mandatory = [
                "GenAI implementation literacy",
                "Prompting patterns and RAG",
                "Evaluation frameworks (LLM-as-judge)",
                "Product/Program execution",
                "PRD and user story writing",
                "Regulated domain experience",
                "Communication and structuring"
            ]
            
            highly_desired = [
                "Workflow tools shipping",
                "Document processing",
                "SQL and analytics",
                "UX collaboration"
            ]
            
            excluded = [
                "LLM researchers",
                "Model trainers",
                "Deep ML (PyTorch)",
                "Pure backend/frontend engineers"
            ]
            
            for skill_name in mandatory:
                summary.mandatory_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.MANDATORY,
                    keywords=self._generate_keywords(skill_name),
                    context="Must-have"
                ))
            
            for skill_name in highly_desired:
                summary.highly_desired_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.HIGHLY_DESIRED,
                    keywords=self._generate_keywords(skill_name),
                    context="Highly desired"
                ))
            
            for skill_name in excluded:
                summary.excluded_skills.append(JDSkill(
                    name=skill_name,
                    priority=SkillPriority.EXCLUDED,
                    keywords=self._generate_keywords(skill_name),
                    context="Not looking for"
                ))
        
        else:
            # Try improved regex parsing
            summary = self.jd_analyzer.analyze_jd(jd_text)
        
        return summary
    
    def _generate_keywords(self, skill_name: str) -> List[str]:
        """Generate semantic keywords"""
        keywords = [skill_name.lower()]
        skill_lower = skill_name.lower()
        
        # Add variants
        variants = {
            'genai': ['genai', 'gen ai', 'generative ai', 'llm'],
            'rag': ['rag', 'retrieval augmented', 'vector search', 'semantic search'],
            'prompt': ['prompting', 'prompt engineering', 'prompt design'],
            'python': ['python', 'python3', 'py'],
            'aws': ['aws', 'amazon web services'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s'],
            'pharma': ['pharma', 'pharmaceutical', 'life sciences', 'healthcare'],
            'product': ['product management', 'product owner', 'pm'],
            'prd': ['prd', 'product requirements', 'user stories'],
        }
        
        for key, values in variants.items():
            if key in skill_lower:
                keywords.extend(values)
        
        return list(set(keywords))[:10]


# Export
__all__ = ['HybridSmartValidator']
