"""
Simplified Evidence Display for Recruiters
==========================================

Transforms the complex Evidence Ledger into a recruiter-friendly interface
with clear visual indicators and simplified explanations.

Key Improvements:
1. Auto-deduplicates evidence (shows only best evidence per skill)
2. Color-coded visual indicators
3. Plain English explanations
4. Hides technical jargon
5. Focus on actionable insights
"""

import streamlit as st
import pandas as pd
from typing import List, Dict
from enhanced_semantic_matcher import EnhancedSkillValidationResult, ExperienceDepth


def display_simplified_evidence(
    validated_skills: List[EnhancedSkillValidationResult],
    weak_skills: List[EnhancedSkillValidationResult],
    ignored_skills: List[EnhancedSkillValidationResult],
    missing_skills: List[EnhancedSkillValidationResult]
):
    """
    Display evidence in a recruiter-friendly format.
    
    Args:
        validated_skills: List of validated skills
        weak_skills: List of weak evidence skills
        ignored_skills: List of ignored skills
        missing_skills: List of missing skills
    """
    
    # Create tabs for different skill categories
    tab1, tab2, tab3, tab4 = st.tabs([
        "✅ Validated Skills",
        "⚠️ Weak Evidence",
        "⊘ Ignored (Skills-Only)",
        "❌ Missing Skills"
    ])
    
    with tab1:
        st.write("**Skills with proven hands-on experience**")
        if validated_skills:
            _display_validated_skills(validated_skills)
        else:
            st.info("No skills met the validation criteria")
    
    with tab2:
        st.write("**Skills mentioned but lacking strong evidence - probe in interview**")
        if weak_skills:
            _display_weak_skills(weak_skills)
        else:
            st.success("No weak evidence skills - all claims are strong!")
    
    with tab3:
        st.write("**Skills listed in resume but no project/work context - likely resume padding**")
        if ignored_skills:
            _display_ignored_skills(ignored_skills)
        else:
            st.success("No ignored skills - all listed skills have context!")
    
    with tab4:
        st.write("**Skills required by JD but not found in resume**")
        if missing_skills:
            _display_missing_skills(missing_skills)
        else:
            st.success("No missing skills - candidate has all required skills!")


def _display_validated_skills(skills: List[EnhancedSkillValidationResult]):
    """Display validated skills with clear visual indicators."""
    
    # Separate priority and non-priority
    priority_skills = [s for s in skills if s.priority_skill]
    other_skills = [s for s in skills if not s.priority_skill]
    
    if priority_skills:
        st.subheader("🎯 Priority Skills (Must-Have)")
        for skill in priority_skills:
            _render_skill_card(skill, is_priority=True)
    
    if other_skills:
        st.subheader("📌 Other Validated Skills")
        for skill in other_skills:
            _render_skill_card(skill, is_priority=False)


def _render_skill_card(skill: EnhancedSkillValidationResult, is_priority: bool):
    """Render a single skill card with visual indicators."""
    
    # Determine color based on hands-on score
    if skill.hands_on_score >= 0.85:
        color = "🟢"  # Green - Excellent
        level = "Excellent"
    elif skill.hands_on_score >= 0.70:
        color = "🟡"  # Yellow - Good
        level = "Good"
    elif skill.hands_on_score >= 0.55:
        color = "🟠"  # Orange - Moderate
        level = "Moderate"
    else:
        color = "🔴"  # Red - Weak
        level = "Weak"
    
    # Get experience depth label
    exp_depth = getattr(skill, 'experience_depth', ExperienceDepth.NOT_FOUND)
    depth_emoji = {
        ExperienceDepth.EXPERT: "⭐⭐⭐",
        ExperienceDepth.PROFICIENT: "⭐⭐",
        ExperienceDepth.COMPETENT: "⭐",
        ExperienceDepth.BASIC: "◐",
        ExperienceDepth.MENTIONED_ONLY: "○",
        ExperienceDepth.NOT_FOUND: "○"
    }
    
    with st.expander(
        f"{color} **{skill.skill_name}** {depth_emoji.get(exp_depth, '')} "
        f"{'🎯 PRIORITY' if is_priority else ''} — {skill.hands_on_score:.0%} hands-on score",
        expanded=False
    ):
        # Simple metrics row
        col1, col2, col3 = st.columns(3)
        col1.metric("Score", f"{skill.hands_on_score:.0%}", f"{level}")
        col2.metric("Experience Level", exp_depth.value.title())
        
        # Has metrics indicator
        has_metrics = False
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            has_metrics = any(
                getattr(e, 'has_metrics', False) for e in skill.enhanced_evidence
            )
        col3.metric("Has Metrics", "✅ Yes" if has_metrics else "❌ No")
        
        # Evidence in plain English
        st.write("**Evidence from Resume:**")
        st.info(skill.reasoning)
        
        # Show actual evidence if available
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            best_evidence = skill.enhanced_evidence[0]
            
            with st.expander("📄 View Resume Excerpt", expanded=False):
                st.caption(f"*Found in: {best_evidence.location}*")
                st.text(f'"{best_evidence.evidence_text[:300]}..."')
                
                # Show what made this strong
                indicators = []
                if hasattr(best_evidence, 'verb_intensity'):
                    indicators.append(f"Action level: {best_evidence.verb_intensity.value}")
                if hasattr(best_evidence, 'has_metrics') and best_evidence.has_metrics:
                    indicators.append("✅ Includes measurable outcomes")
                if hasattr(best_evidence, 'has_outcomes') and best_evidence.has_outcomes:
                    indicators.append("✅ Describes results/impact")
                if hasattr(best_evidence, 'project_duration_months') and best_evidence.project_duration_months:
                    indicators.append(f"Duration: ~{best_evidence.project_duration_months} months")
                
                if indicators:
                    st.write("**Why this validates the skill:**")
                    for indicator in indicators:
                        st.write(f"  • {indicator}")


def _display_weak_skills(skills: List[EnhancedSkillValidationResult]):
    """Display weak evidence skills with interviewer guidance."""
    
    st.warning("⚠️ These skills need verification in the interview")
    
    for skill in skills:
        with st.expander(f"⚠️ {skill.skill_name} — {skill.hands_on_score:.0%} confidence"):
            st.write("**Why it's weak:**")
            st.write(skill.reasoning)
            
            st.write("\n**Suggested Interview Questions:**")
            st.write(f"• Can you walk me through a specific project where you used {skill.skill_name}?")
            st.write(f"• What was your role in that project?")
            st.write(f"• What specific {skill.skill_name} techniques or tools did you use?")
            st.write(f"• What was the outcome? Any measurable results?")


def _display_ignored_skills(skills: List[EnhancedSkillValidationResult]):
    """Display ignored skills with resume padding warning."""
    
    st.warning("These skills appear ONLY in the Skills section with no supporting evidence")
    
    # Group into simple list
    skill_names = [s.skill_name for s in skills]
    
    st.write(f"**{len(skill_names)} skills listed without proof:**")
    st.write(", ".join(skill_names))
    
    st.write("\n**What this means:**")
    st.write("• Candidate may have taken courses or have basic familiarity")
    st.write("• No evidence of actual hands-on work with these technologies")
    st.write("• Ask detailed technical questions to verify true proficiency")
    
    with st.expander("📋 View Details", expanded=False):
        for skill in skills:
            st.write(f"**{skill.skill_name}**")
            st.caption(skill.reasoning)
            st.divider()


def _display_missing_skills(skills: List[EnhancedSkillValidationResult]):
    """Display missing skills with hiring decision guidance."""
    
    # Separate priority and non-priority
    priority_missing = [s for s in skills if hasattr(s, 'priority_skill') and s.priority_skill]
    other_missing = [s for s in skills if not (hasattr(s, 'priority_skill') and s.priority_skill)]
    
    if priority_missing:
        st.error(f"🚨 **CRITICAL: Missing {len(priority_missing)} Priority Skills**")
        st.write("**These are must-have skills you specified:**")
        for skill in priority_missing:
            st.write(f"• ❌ {skill.skill_name}")
        
        st.write("\n**Recommendation:**")
        st.write("• Consider rejecting unless candidate has equivalent skills")
        st.write("• Or use 'Skills Gap Analysis' to see if hire-and-train is viable")
    
    if other_missing:
        st.warning(f"⚠️ **Missing {len(other_missing)} Nice-to-Have Skills**")
        with st.expander("View missing non-priority skills"):
            for skill in other_missing:
                st.write(f"• {skill.skill_name}")


def create_simplified_summary_table(
    validated_skills: List[EnhancedSkillValidationResult],
    priority_skills_input: List[str]
) -> pd.DataFrame:
    """
    Create a simplified summary table (no duplicates, plain English).
    
    Args:
        validated_skills: List of validated skills
        priority_skills_input: List of priority skill names
        
    Returns:
        DataFrame with simplified evidence
    """
    priority_set = set(s.lower().strip() for s in priority_skills_input)
    
    data = []
    for skill in validated_skills:
        is_priority = skill.skill_name.lower() in priority_set
        
        # Get best evidence
        has_metrics = "❌ No"
        evidence_location = "Unknown"
        
        if hasattr(skill, 'enhanced_evidence') and skill.enhanced_evidence:
            best_evidence = skill.enhanced_evidence[0]
            evidence_location = best_evidence.location
            
            if hasattr(best_evidence, 'has_metrics') and best_evidence.has_metrics:
                has_metrics = "✅ Yes"
        
        # Simple depth label
        exp_depth = getattr(skill, 'experience_depth', ExperienceDepth.NOT_FOUND)
        depth_label = {
            ExperienceDepth.EXPERT: "⭐⭐⭐ Expert",
            ExperienceDepth.PROFICIENT: "⭐⭐ Proficient",
            ExperienceDepth.COMPETENT: "⭐ Competent",
            ExperienceDepth.BASIC: "◐ Basic",
            ExperienceDepth.MENTIONED_ONLY: "○ Mentioned Only"
        }.get(exp_depth, "Unknown")
        
        # Score level
        score = skill.hands_on_score
        if score >= 0.85:
            score_label = "🟢 Excellent"
        elif score >= 0.70:
            score_label = "🟡 Good"
        elif score >= 0.55:
            score_label = "🟠 Moderate"
        else:
            score_label = "🔴 Weak"
        
        data.append({
            "Skill": f"{'🎯 ' if is_priority else ''}{skill.skill_name}",
            "Score": f"{score:.0%}",
            "Level": score_label,
            "Experience": depth_label,
            "Has Metrics": has_metrics,
            "Found In": evidence_location
        })
    
    return pd.DataFrame(data)


def display_decision_guidance(
    overall_fit: float,
    validated_count: int,
    priority_validated: int,
    total_priority: int,
    missing_priority: int
):
    """
    Display hiring decision guidance based on analysis.
    
    Args:
        overall_fit: Overall fit score (0-1)
        validated_count: Number of validated skills
        priority_validated: Number of priority skills validated
        total_priority: Total number of priority skills
        missing_priority: Number of missing priority skills
    """
    st.divider()
    st.subheader("💡 Hiring Recommendation")
    
    # Determine recommendation
    if overall_fit >= 0.85 and missing_priority == 0:
        st.success("✅ **STRONG MATCH - Recommend Fast-Track to Interview**")
        st.write("**Why:**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Excellent)")
        st.write(f"• All {total_priority} priority skills validated")
        st.write(f"• {validated_count} total skills with proven hands-on experience")
        
        st.write("\n**Next Steps:**")
        st.write("1. Schedule technical interview")
        st.write("2. Use 'Generate Interview Questions' for evidence-based questions")
        st.write("3. Verify top claims with specific examples")
        
    elif overall_fit >= 0.70 and priority_validated >= total_priority * 0.75:
        st.info("🟡 **GOOD MATCH - Recommend Phone Screen**")
        st.write("**Why:**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Good)")
        st.write(f"• {priority_validated}/{total_priority} priority skills validated")
        st.write(f"• {validated_count} total validated skills")
        
        if missing_priority > 0:
            st.write(f"\n⚠️ **Note:** Missing {missing_priority} priority skill(s)")
            st.write("**Recommended Action:**")
            st.write("• Assess if missing skills are learnable quickly")
            st.write("• Consider 'Skills Gap Analysis' for training path")
        
        st.write("\n**Next Steps:**")
        st.write("1. Phone screen to assess depth of validated skills")
        st.write("2. Ask about missing/weak skills")
        st.write("3. If phone screen passes, proceed to technical interview")
        
    elif overall_fit >= 0.60:
        st.warning("🟠 **MODERATE MATCH - Technical Assessment Recommended**")
        st.write("**Why:**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Moderate)")
        st.write(f"• {priority_validated}/{total_priority} priority skills validated")
        
        if missing_priority > 0:
            st.write(f"• ⚠️ Missing {missing_priority} priority skill(s)")
        
        st.write("\n**Recommended Actions:**")
        st.write("1. Use 'Skills Gap Analysis' to evaluate hire-and-train viability")
        st.write("2. Send technical assessment to verify claimed skills")
        st.write("3. Consider for junior/mid-level roles if senior requirement")
        
    else:
        st.error("🔴 **WEAK MATCH - Likely Reject**")
        st.write("**Why:**")
        st.write(f"• Overall fit: {overall_fit:.0%} (Below threshold)")
        st.write(f"• Only {priority_validated}/{total_priority} priority skills validated")
        st.write(f"• Missing {missing_priority} priority skill(s)")
        
        st.write("\n**Recommendation:** Keep searching for better-matched candidates")
        
        st.write("\n**Exception Cases:**")
        st.write("• If talent market is extremely tight, consider:")
        st.write("  - 'Skills Gap Analysis' for extensive training path")
        st.write("  - Adjusting role requirements")
        st.write("  - Offering junior-level position")


if __name__ == "__main__":
    print("Simplified Evidence Display - Ready for Integration")
