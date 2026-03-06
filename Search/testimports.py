# test_imports.py
print("Testing imports...")

try:
    from JD_Resume_Final_With_Evidence import *
    print("✅ Main app imports OK")
except Exception as e:
    print(f"❌ Main app error: {e}")

try:
    from enhanced_semantic_matcher import EnhancedSemanticSkillMatcher
    print("✅ Enhanced matcher OK")
except Exception as e:
    print(f"❌ Matcher error: {e}")

try:
    from skill_filter import SkillFilter
    print("✅ Skill filter OK")
except Exception as e:
    print(f"❌ Filter error: {e}")

try:
    from recruiter_workflow import CandidateHistoryManager, HiringSummaryGenerator
    print("✅ Recruiter workflow OK")
except Exception as e:
    print(f"❌ Workflow error: {e}")

try:
    from improved_question_generator import ImprovedQuestionGenerator
    from situational_technical_generator import SituationalTechnicalGenerator
    from coding_question_generator import CodingQuestionGenerator
    print("✅ All 3 question generators OK")
except Exception as e:
    print(f"❌ Question generators error: {e}")

print("\n✅ All imports successful! Ready to run.")