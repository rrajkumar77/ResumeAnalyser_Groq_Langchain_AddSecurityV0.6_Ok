"""
Skill Filter Utility
====================

Filters out false positives from skill extraction:
- Geographic locations (cities, states, countries)
- Company names
- Job titles
- Generic business terms
- Non-technical words
"""

import re
from typing import List, Set


class SkillFilter:
    """Filters out non-skill terms from extracted skill lists."""
    
    # Common false positives to exclude
    LOCATIONS = {
        # US Cities
        'austin', 'boston', 'chicago', 'dallas', 'denver', 'houston', 
        'los angeles', 'la', 'miami', 'new york', 'nyc', 'philadelphia', 
        'phoenix', 'san antonio', 'san diego', 'san francisco', 'sf', 
        'seattle', 'washington dc', 'dc', 'atlanta', 'portland', 'charlotte',
        'detroit', 'las vegas', 'orlando', 'indianapolis', 'columbus',
        
        # States
        'california', 'texas', 'florida', 'new york', 'pennsylvania',
        'illinois', 'ohio', 'georgia', 'north carolina', 'michigan',
        'virginia', 'washington', 'arizona', 'massachusetts', 'tennessee',
        'indiana', 'missouri', 'maryland', 'wisconsin', 'colorado',
        'minnesota', 'south carolina', 'alabama', 'louisiana', 'kentucky',
        'oregon', 'oklahoma', 'connecticut', 'utah', 'iowa', 'nevada',
        
        # International Cities
        'singapore', 'london', 'tokyo', 'paris', 'berlin', 'sydney',
        'toronto', 'vancouver', 'mumbai', 'bangalore', 'delhi', 'chennai',
        'hyderabad', 'pune', 'dublin', 'amsterdam', 'zurich', 'hong kong',
        'shanghai', 'beijing', 'seoul', 'melbourne', 'auckland',
        
        # Countries
        'usa', 'united states', 'uk', 'united kingdom', 'canada', 
        'australia', 'india', 'germany', 'france', 'japan', 'china',
        'singapore', 'ireland', 'netherlands', 'switzerland', 'sweden',
        'norway', 'denmark', 'finland', 'spain', 'italy', 'brazil',
        
        # Regions
        'north america', 'south america', 'europe', 'asia', 'apac',
        'emea', 'latam', 'middle east', 'east coast', 'west coast'
    }
    
    JOB_TITLES = {
        'engineer', 'developer', 'architect', 'manager', 'director',
        'senior', 'junior', 'lead', 'principal', 'staff', 'consultant',
        'analyst', 'specialist', 'administrator', 'coordinator',
        'supervisor', 'executive', 'officer', 'president', 'vp',
        'vice president', 'ceo', 'cto', 'cio', 'cfo', 'head of',
        'team lead', 'tech lead', 'scrum master', 'product owner'
    }
    
    COMPANY_INDICATORS = {
        'inc', 'llc', 'ltd', 'corporation', 'corp', 'company', 'co',
        'technologies', 'tech', 'systems', 'solutions', 'services',
        'consulting', 'group', 'partners', 'associates', 'enterprises'
    }
    
    GENERIC_TERMS = {
        # Soft skills / generic terms
        'communication', 'teamwork', 'leadership', 'problem solving',
        'analytical', 'critical thinking', 'collaboration', 'flexibility',
        'adaptability', 'creativity', 'innovation', 'detail oriented',
        'time management', 'organization', 'multitasking', 'prioritization',
        
        # Business terms
        'business', 'enterprise', 'corporate', 'commercial', 'industrial',
        'professional', 'strategic', 'operational', 'tactical',
        'client', 'customer', 'stakeholder', 'vendor', 'partner',
        
        # Education terms
        'degree', 'bachelor', 'master', 'phd', 'mba', 'certification',
        'diploma', 'graduate', 'undergraduate', 'college', 'university',
        
        # Time/Experience
        'years', 'months', 'experience', 'background', 'knowledge',
        'understanding', 'familiarity', 'exposure', 'working knowledge',
        
        # Generic descriptors
        'strong', 'excellent', 'good', 'solid', 'proven', 'demonstrated',
        'extensive', 'comprehensive', 'thorough', 'deep', 'advanced',
        'basic', 'intermediate', 'expert', 'proficient'
    }
    
    # Terms that are too short and ambiguous
    TOO_SHORT = {'ai', 'ml', 'qa', 'ui', 'ux', 'ci', 'cd', 'os', 'db'}
    
    # Technical terms that ARE valid skills (whitelist for short terms)
    VALID_SHORT_TERMS = {
        'c', 'c++', 'c#', 'r', 'go', 'sql', 'aws', 'gcp', 'api', 'etl',
        'ci/cd', 'ui/ux', 'nlp', 'cv', 'ml', 'ai', 'iot', 'vr', 'ar'
    }
    
    @classmethod
    def is_valid_skill(cls, term: str) -> bool:
        """
        Check if a term is a valid technical skill.
        
        Args:
            term: Skill term to validate
            
        Returns:
            True if valid skill, False if false positive
        """
        if not term:
            return False
        
        term_lower = term.lower().strip()
        
        # Check whitelist for short terms
        if term_lower in cls.VALID_SHORT_TERMS:
            return True
        
        # Too short and not in whitelist
        if len(term_lower) <= 2 and term_lower not in cls.VALID_SHORT_TERMS:
            return False
        
        # Check if it's a location
        if term_lower in cls.LOCATIONS:
            return False
        
        # Check if it's a job title
        if term_lower in cls.JOB_TITLES:
            return False
        
        # Check if it's a generic term
        if term_lower in cls.GENERIC_TERMS:
            return False
        
        # Check if it contains company indicators
        for indicator in cls.COMPANY_INDICATORS:
            if indicator in term_lower:
                return False
        
        # Check if it's mostly non-alphanumeric
        alphanumeric_count = sum(c.isalnum() for c in term)
        if alphanumeric_count < len(term) * 0.5:
            return False
        
        # Passed all filters
        return True
    
    @classmethod
    def filter_skills(cls, skills: List[str]) -> List[str]:
        """
        Filter a list of skills to remove false positives.
        
        Args:
            skills: List of extracted skills
            
        Returns:
            Filtered list of valid technical skills
        """
        return [skill for skill in skills if cls.is_valid_skill(skill)]
    
    @classmethod
    def add_custom_exclusions(cls, exclusions: List[str]):
        """
        Add custom terms to exclude.
        
        Args:
            exclusions: List of terms to exclude
        """
        for term in exclusions:
            cls.GENERIC_TERMS.add(term.lower().strip())


if __name__ == "__main__":
    # Test examples
    test_skills = [
        "Python", "AWS", "Singapore", "Austin", "SQL", 
        "Machine Learning", "New York", "leadership", 
        "Docker", "ai", "C++", "experience"
    ]
    
    print("Before filtering:", test_skills)
    filtered = SkillFilter.filter_skills(test_skills)
    print("After filtering:", filtered)
    
    # Should output: ['Python', 'AWS', 'SQL', 'Machine Learning', 'Docker', 'ai', 'C++']
