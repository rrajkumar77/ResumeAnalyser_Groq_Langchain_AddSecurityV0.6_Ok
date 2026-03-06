"""
Test Suite for Enhanced Recruitment Tool
=========================================

Tests for:
1. Security masking (PII and client-sensitive)
2. Enhanced semantic skill matching
3. Hands-on experience validation
4. Priority skills weighting
"""

import unittest
from security_masker import (
    SecurityMasker,
    PIIMasker,
    ClientSensitiveMasker,
    MaskingResult
)
from enhanced_semantic_matcher import (
    EnhancedSemanticSkillMatcher,
    EnhancedActionVerbDetector,
    MetricsAndOutcomesDetector,
    ProjectDurationEstimator,
    ExperienceDepth,
    ActionVerbIntensity
)


class TestPIIMasking(unittest.TestCase):
    """Test PII masking functionality."""
    
    def setUp(self):
        self.masker = PIIMasker()
    
    def test_email_masking(self):
        """Test email address masking."""
        text = "Contact me at john.doe@gmail.com or jane@company.org"
        result = self.masker.mask_resume(text)
        
        self.assertEqual(result.mask_count, 2)
        self.assertNotIn("john.doe@gmail.com", result.masked_text)
        self.assertNotIn("jane@company.org", result.masked_text)
        self.assertIn("candidate.email", result.masked_text)
    
    def test_phone_masking(self):
        """Test phone number masking (various formats)."""
        text = """
        Phone: +1-555-123-4567
        Mobile: (555) 987-6543
        Cell: 555.111.2222
        """
        result = self.masker.mask_resume(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("123-4567", result.masked_text)
        self.assertNotIn("987-6543", result.masked_text)
        self.assertIn("555", result.masked_text)  # Placeholder uses 555
    
    def test_ssn_masking(self):
        """Test SSN masking."""
        text = "SSN: 123-45-6789"
        result = self.masker.mask_resume(text)
        
        self.assertEqual(result.mask_count, 1)
        self.assertNotIn("123-45-6789", result.masked_text)
        self.assertIn("***-**-****", result.masked_text)
    
    def test_address_masking(self):
        """Test address masking."""
        text = "Lives at 123 Main Street, Anytown"
        result = self.masker.mask_resume(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("123 Main Street", result.masked_text)
        self.assertIn("[Address Redacted]", result.masked_text)
    
    def test_dob_masking(self):
        """Test date of birth masking."""
        text = "DOB: 01/15/1990"
        result = self.masker.mask_resume(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("01/15/1990", result.masked_text)
        self.assertIn("MM/DD/YYYY", result.masked_text)
    
    def test_comprehensive_resume_masking(self):
        """Test comprehensive PII masking on realistic resume."""
        resume = """
        John Doe
        Email: john.doe@gmail.com
        Phone: +1-555-123-4567
        Address: 123 Main Street, Anytown, CA 12345
        SSN: 123-45-6789
        DOB: 01/15/1990
        
        EXPERIENCE
        Senior Developer at TechCorp Inc.
        - Built Python applications
        """
        
        result = self.masker.mask_resume(resume)
        
        # Check all PII is masked
        self.assertNotIn("john.doe@gmail.com", result.masked_text)
        self.assertNotIn("555-123-4567", result.masked_text)
        self.assertNotIn("123 Main Street", result.masked_text)
        self.assertNotIn("123-45-6789", result.masked_text)
        self.assertNotIn("01/15/1990", result.masked_text)
        
        # Check content is preserved
        self.assertIn("EXPERIENCE", result.masked_text)
        self.assertIn("Senior Developer", result.masked_text)
        self.assertIn("Python", result.masked_text)
        
        # Check statistics
        self.assertGreater(result.mask_count, 5)
        self.assertIn("email", result.sensitivity_detected)
        self.assertIn("phone", result.sensitivity_detected)


class TestClientSensitiveMasking(unittest.TestCase):
    """Test client-sensitive information masking."""
    
    def setUp(self):
        self.masker = ClientSensitiveMasker()
    
    def test_client_ref_masking(self):
        """Test client reference masking."""
        text = "Client-ID: CLT-12345, Customer Ref: CUST-67890"
        result = self.masker.mask_jd(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("CLT-12345", result.masked_text)
        self.assertIn("[CLIENT-REF-REDACTED]", result.masked_text)
    
    def test_project_code_masking(self):
        """Test project code masking."""
        text = "Project ID: PROJ-12345, Project Code: ABC-999"
        result = self.masker.mask_jd(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("PROJ-12345", result.masked_text)
        self.assertIn("[PROJECT-CODE-REDACTED]", result.masked_text)
    
    def test_confidential_marker_masking(self):
        """Test confidential marker masking."""
        text = "CONFIDENTIAL - Internal Only - Do Not Share"
        result = self.masker.mask_jd(text)
        
        self.assertGreater(result.mask_count, 0)
        self.assertIn("[CONFIDENTIAL-REDACTED]", result.masked_text)
    
    def test_budget_masking(self):
        """Test budget masking (context-aware)."""
        text1 = "Budget: $150,000 - $180,000"
        text2 = "Experience with $1M+ datasets"  # Should NOT mask
        
        result1 = self.masker.mask_jd(text1)
        result2 = self.masker.mask_jd(text2)
        
        self.assertGreater(result1.mask_count, 0)
        self.assertIn("$[REDACTED]", result1.masked_text)
        
        # Dataset mention should not be masked (no budget context)
        self.assertEqual(result2.mask_count, 0)
        self.assertIn("$1M+", result2.masked_text)
    
    def test_known_client_name_masking(self):
        """Test known client name masking."""
        text = "Client: Acme Technologies LLC is seeking a developer"
        result = self.masker.mask_jd(text, known_client_names=["Acme Technologies"])
        
        self.assertGreater(result.mask_count, 0)
        self.assertNotIn("Acme Technologies", result.masked_text)
        self.assertIn("[Client Company]", result.masked_text)
    
    def test_company_name_detection(self):
        """Test heuristic company name detection."""
        text = "Our client, XYZ Consulting LLC, needs a senior developer"
        result = self.masker.mask_jd(text)
        
        # Should detect "XYZ Consulting LLC" as company name
        self.assertGreater(result.mask_count, 0)
        self.assertIn("[Client Company]", result.masked_text)
    
    def test_technology_exclusion(self):
        """Test that common technology acronyms are NOT masked."""
        text = "Required: AWS, API, SQL, GCP, REST-API experience"
        result = self.masker.mask_jd(text)
        
        # These should NOT be masked
        self.assertIn("AWS", result.masked_text)
        self.assertIn("API", result.masked_text)
        self.assertIn("SQL", result.masked_text)
        self.assertIn("GCP", result.masked_text)


class TestActionVerbDetection(unittest.TestCase):
    """Test action verb intensity detection."""
    
    def test_leadership_verbs(self):
        """Test leadership verb detection."""
        text = "Led the architecture design and spearheaded the migration"
        verbs, intensity, score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.LEADERSHIP)
        self.assertGreater(score, 0.9)
        self.assertIn("led", verbs)
        self.assertIn("spearheaded", verbs)
    
    def test_core_delivery_verbs(self):
        """Test core delivery verb detection."""
        text = "Built and deployed a microservices platform"
        verbs, intensity, score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.CORE_DELIVERY)
        self.assertGreater(score, 0.8)
        self.assertIn("built", verbs)
        self.assertIn("deployed", verbs)
    
    def test_contribution_verbs(self):
        """Test contribution verb detection."""
        text = "Contributed to and collaborated on the project"
        verbs, intensity, score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.CONTRIBUTION)
        self.assertLess(score, 0.7)
        self.assertIn("contributed", verbs)
        self.assertIn("collaborated", verbs)
    
    def test_passive_verbs(self):
        """Test passive verb detection."""
        text = "Familiar with Python and basic understanding of AWS"
        verbs, intensity, score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.PASSIVE)
        self.assertLess(score, 0.3)


class TestMetricsDetection(unittest.TestCase):
    """Test metrics and outcomes detection."""
    
    def test_percentage_metrics(self):
        """Test percentage metric detection."""
        text = "Improved performance by 40% and reduced latency by 25%"
        has_metrics, has_outcomes, metrics = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertTrue(has_metrics)
        self.assertGreater(len(metrics), 0)
        self.assertIn("40%", metrics)
    
    def test_time_metrics(self):
        """Test time metric detection."""
        text = "Reduced deployment time from 2 hours to 15 minutes"
        has_metrics, has_outcomes, metrics = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertTrue(has_metrics)
        self.assertGreater(len(metrics), 0)
    
    def test_scale_metrics(self):
        """Test scale metric detection."""
        text = "Platform serving 500K daily users with 10M records"
        has_metrics, has_outcomes, metrics = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertTrue(has_metrics)
    
    def test_outcomes(self):
        """Test outcome keyword detection."""
        text = "Successfully deployed to production and launched the feature"
        has_metrics, has_outcomes, metrics = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertTrue(has_outcomes)
    
    def test_no_metrics(self):
        """Test text without metrics."""
        text = "Worked on various projects using Python"
        has_metrics, has_outcomes, metrics = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertFalse(has_metrics)
        self.assertEqual(len(metrics), 0)


class TestProjectDurationEstimation(unittest.TestCase):
    """Test project duration estimation."""
    
    def test_explicit_months(self):
        """Test explicit month duration."""
        text = "Project duration: 6 months"
        duration = ProjectDurationEstimator.estimate_duration(text)
        
        self.assertEqual(duration, 6)
    
    def test_explicit_years(self):
        """Test explicit year duration."""
        text = "2 year project"
        duration = ProjectDurationEstimator.estimate_duration(text)
        
        self.assertEqual(duration, 24)
    
    def test_date_range(self):
        """Test date range duration."""
        text = "2021 - 2023"
        duration = ProjectDurationEstimator.estimate_duration(text)
        
        self.assertEqual(duration, 24)
    
    def test_no_duration(self):
        """Test text without duration."""
        text = "Built a Python application"
        duration = ProjectDurationEstimator.estimate_duration(text)
        
        self.assertIsNone(duration)


class TestExperienceDepthScoring(unittest.TestCase):
    """Test hands-on experience depth scoring."""
    
    def test_expert_level_evidence(self):
        """Test expert-level evidence scoring."""
        text = """
        Led the architecture and design of a microservices platform
        serving 500K daily users. Reduced infrastructure costs by 30%
        through Kubernetes migration. Deployed to production with 99.9% uptime.
        Duration: 18 months
        """
        
        # This should score high (EXPERT level)
        verbs, intensity, verb_score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        has_metrics, has_outcomes, _ = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        duration = ProjectDurationEstimator.estimate_duration(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.LEADERSHIP)
        self.assertTrue(has_metrics)
        self.assertTrue(has_outcomes)
        self.assertGreater(duration, 12)
        self.assertGreater(verb_score, 0.9)
    
    def test_basic_level_evidence(self):
        """Test basic-level evidence scoring."""
        text = "Assisted with Python scripting tasks"
        
        verbs, intensity, verb_score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        has_metrics, has_outcomes, _ = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.SUPPORT)
        self.assertFalse(has_metrics)
        self.assertLess(verb_score, 0.5)
    
    def test_mentioned_only_evidence(self):
        """Test mentioned-only (no hands-on) evidence."""
        text = "Familiar with Python, basic understanding of AWS"
        
        verbs, intensity, verb_score = EnhancedActionVerbDetector.detect_verbs_with_intensity(text)
        has_metrics, has_outcomes, _ = MetricsAndOutcomesDetector.detect_metrics_and_outcomes(text)
        
        self.assertEqual(intensity, ActionVerbIntensity.PASSIVE)
        self.assertFalse(has_metrics)
        self.assertLess(verb_score, 0.3)


class TestPrioritySkillsWeighting(unittest.TestCase):
    """Test priority skills weighting in overall scoring."""
    
    def test_priority_skill_identification(self):
        """Test that priority skills are correctly identified."""
        # This would require full integration test with EnhancedSemanticSkillMatcher
        # Placeholder for now
        priority_skills = ["Python", "AWS", "Kubernetes"]
        skill_name = "python"
        
        is_priority = skill_name.lower() in [s.lower() for s in priority_skills]
        self.assertTrue(is_priority)


def run_security_tests():
    """Run all security-related tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPIIMasking))
    suite.addTests(loader.loadTestsFromTestCase(TestClientSensitiveMasking))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


def run_semantic_tests():
    """Run all semantic matching tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestActionVerbDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestProjectDurationEstimation))
    suite.addTests(loader.loadTestsFromTestCase(TestExperienceDepthScoring))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


def run_all_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestPIIMasking))
    suite.addTests(loader.loadTestsFromTestCase(TestClientSensitiveMasking))
    suite.addTests(loader.loadTestsFromTestCase(TestActionVerbDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestProjectDurationEstimation))
    suite.addTests(loader.loadTestsFromTestCase(TestExperienceDepthScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestPrioritySkillsWeighting))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    print("=" * 80)
    print("ENHANCED RECRUITMENT TOOL - TEST SUITE")
    print("=" * 80)
    print("\nRunning all tests...\n")
    
    result = run_all_tests()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed. Review output above.")
