#!/usr/bin/env python3
"""Unit tests for cognitive_load_calculator.py against Mayer & Chen calibration curves."""

import unittest
from tools.cognitive_load_calculator import CognitiveLoadCalculator, CalculationResult


class TestCognitiveLoadCalculator(unittest.TestCase):
    """Test cases per Mayer & Chen (2024) and Dastin (2023) priors."""

    def setUp(self):
        self.calculator = CognitiveLoadCalculator()

    def test_routine_task_low_pressure_high_confidence(self):
        """Scenario 1: Routine task, low pressure → ~40% delegation, HIGH confidence."""
        result = self.calculator.calculate(
            task_complexity=2,
            time_pressure="low",
            domain_familiarity="established",
            supporting_evidence_n=5,
        )
        
        # Should be near bottom of Goldilocks zone
        self.assertAlmostEqual(result.recommended_delegation_pct, 40.0, delta=5)
        self.assertEqual(result.confidence_level, "[HIGH CONFIDENCE]")
        self.assertGreaterEqual(result.confidence_numeric, 0.85)

    def test_complex_novel_task_critical_pressure_low_confidence(self):
        """Scenario 2: Complex novel task, critical pressure → higher delegation (~60%), LOW confidence."""
        result = self.calculator.calculate(
            task_complexity=9,
            time_pressure="critical",
            domain_familiarity="novel",
            supporting_evidence_n=2,
        )
        
        # Should be at top of Goldilocks zone due to high cognitive load
        self.assertGreaterEqual(result.recommended_delegation_pct, 55.0)
        self.assertLessEqual(result.recommended_delegation_pct, 65.0)
        self.assertEqual(result.confidence_level, "[LOW CONFIDENCE - RECOMMEND MANUAL REVIEW]")
        self.assertLess(result.confidence_numeric, 0.60)

    def test_moderate_normal_conditions_moderate_confidence(self):
        """Scenario 3: Moderate complexity, normal conditions → ~50% delegation, MODERATE confidence."""
        result = self.calculator.calculate(
            task_complexity=5,
            time_pressure="normal",
            domain_familiarity="developing",
            supporting_evidence_n=4,
        )
        
        # Should land squarely in middle of Goldilocks zone
        self.assertAlmostEqual(result.recommended_delegation_pct, 50.0, delta=8)
        self.assertEqual(result.confidence_level, "[MODERATE CONFIDENCE]")
        self.assertGreaterEqual(result.confidence_numeric, 0.60)
        self.assertLess(result.confidence_numeric, 0.85)

    def test_clamped_to_goldilocks_zone(self):
        """Verify output never exceeds 40-60% bounds without extreme context justification."""
        # Extreme inputs that would push beyond bounds if not clamped
        result = self.calculator.calculate(
            task_complexity=10,  # Maximum complexity
            time_pressure="critical",
            domain_familiarity="novel",
            supporting_evidence_n=1,  # Minimum evidence
        )
        
        # Even with maximum stressors, should stay within Goldilocks zone
        self.assertGreaterEqual(result.recommended_delegation_pct, 40.0)
        self.assertLessEqual(result.recommended_delegation_pct, 60.0)

    def test_multi_option_structure(self):
        """Verify all three options are present with correct structure."""
        result = self.calculator.calculate(
            task_complexity=5,
            time_pressure="normal",
            domain_familiarity="established",
            supporting_evidence_n=3,
        )
        
        self.assertEqual(len(result.options), 3)
        
        option_labels = [opt["label"] for opt in result.options]
        self.assertIn("Option A — Conservative", option_labels)
        self.assertIn("Option B — Balanced (Recommended)", option_labels)
        self.assertIn("Option C — Aggressive", option_labels)
        
        # Each option must have required fields
        for option in result.options:
            self.assertIn("delegation_pct", option)
            self.assertIn("description", option)
            self.assertIn("pros", option)
            self.assertIn("cons", option)
            self.assertIn("recommended_when", option)


class TestCalculationResult(unittest.TestCase):
    """Test CalculationResult dataclass behavior."""

    def test_timestamp_generation(self):
        """Timestamp should be auto-generated ISO8601 format."""
        result = CalculationResult(
            recommended_delegation_pct=45.0,
            confidence_level="[MODERATE CONFIDENCE]",
            confidence_numeric=0.70,
            options=[],
            rationale="Test rationale",
        )
        
        # Should contain 'Z' suffix indicating UTC
        self.assertIn("T", result.timestamp)
        self.assertIn("Z", result.timestamp)


if __name__ == "__main__":
    unittest.main()
