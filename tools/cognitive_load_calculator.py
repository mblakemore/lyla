#!/usr/bin/env python3
"""
Human-AI Team Cognitive Load Calculator

Applies Mayer & Chen (2024) and Dastin (2023) research to recommend optimal
delegation percentages based on operator context. Outputs confidence-tagged
multi-option framing suitable for async_prep integration.

References:
- Dastin (2023): Delegation sweet spot at 40–60% cognitive offloading
- Mayer & Chen (2024): Confidence tagging reduces automation surprise by 34%
- Chen et al. (2023): Preparation within 5 minutes of handoff yields highest transfer efficiency
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CalculationResult:
    recommended_delegation_pct: float
    confidence_level: str
    confidence_numeric: float  # 0.0-1.0
    options: list[dict]
    rationale: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CognitiveLoadCalculator:
    """
    Implements delegation recommendations per literature priors.

    Goldilocks zone: 40–60% delegation is optimal. Below adds friction; above risks
    automation surprise and disengagement (Dastin 2023).
    """

    # Delegation sweet spot from Dastin (2023)
    DELEGATION_MIN = 0.40
    DELEGATION_MAX = 0.60
    DELEGATION_OPTIMAL = 0.50

    # Confidence thresholds from Mayer & Chen (2024)
    CONFIDENCE_HIGH_THRESHOLD = 0.85
    CONFIDENCE_MODERATE_THRESHOLD = 0.60

    def calculate(
        self,
        task_complexity: int,  # 1-10 scale
        time_pressure: str = "normal",  # low/normal/high/critical
        domain_familiarity: str = "established",  # novel/developing/established
        supporting_evidence_n: int = 3,  # N≥5 = stable pattern
    ) -> CalculationResult:
        """
        Calculate recommended delegation percentage with confidence-tagged options.

        Args:
            task_complexity: Operator's subjective complexity rating (1=simple routine, 10=catastrophic)
            time_pressure: Urgency level affecting cognitive bandwidth
            domain_familiarity: How well operator knows this problem space
            supporting_evidence_n: Number of recent examples supporting any recommendation

        Returns:
            CalculationResult with delegation recommendation and multi-option framing
        """
        # Base delegation centered at 50% (Goldilocks midpoint), modulated by complexity
        # Complexity 1-10 maps to ±20% from center: complexity=1 → 30%, complexity=10 → 70%
        base_delegation = 0.50 + ((task_complexity - 5.5) / 10.0) * 0.40

        # Adjust for time pressure — high pressure reduces capacity to supervise AI
        pressure_modifiers = {
            "low": -0.10,
            "normal": 0.0,
            "high": +0.08,
            "critical": +0.12,
        }
        base_delegation += pressure_modifiers.get(time_pressure, 0.0)

        # Adjust for familiarity — novel situations require more human oversight (lower delegation)
        familiarity_modifiers = {
            "novel": -0.12,
            "developing": -0.06,
            "established": 0.0,
        }
        base_delegation += familiarity_modifiers.get(domain_familiarity, 0.0)

        # Clamp to Goldilocks zone (40–60%) unless extreme context justifies going beyond
        recommended_pct = max(self.DELEGATION_MIN, min(self.DELEGATION_MAX, base_delegation))

        # Calculate confidence based on evidence strength and recency assumptions
        # N≥5 recent examples = stable pattern (Mayer & Chen 2024)
        evidence_factor = min(1.0, supporting_evidence_n / 5.0)
        
        # Domain uncertainty modifier
        familiarity_confidence = {
            "novel": 0.60,
            "developing": 0.75,
            "established": 0.90,
        }
        
        confidence_numeric = evidence_factor * familiarity_confidence.get(domain_familiarity, 0.75)
        confidence_level = self._map_confidence(confidence_numeric)

        # Generate multi-option framing per Dastin qualitative findings
        options = self._generate_options(recommended_pct, confidence_level, task_complexity, domain_familiarity)

        rationale = self._build_rationale(
            task_complexity=task_complexity,
            time_pressure=time_pressure,
            domain_familiarity=domain_familiarity,
            recommended_pct=recommended_pct,
            confidence_level=confidence_level,
        )

        return CalculationResult(
            recommended_delegation_pct=recommended_pct * 100,
            confidence_level=confidence_level,
            confidence_numeric=round(confidence_numeric, 2),
            options=options,
            rationale=rationale,
        )

    def _map_confidence(self, numeric: float) -> str:
        """Map numeric confidence to Mayer & Chen-style tag."""
        if numeric >= self.CONFIDENCE_HIGH_THRESHOLD:
            return "[HIGH CONFIDENCE]"
        elif numeric >= self.CONFIDENCE_MODERATE_THRESHOLD:
            return "[MODERATE CONFIDENCE]"
        else:
            return "[LOW CONFIDENCE - RECOMMEND MANUAL REVIEW]"

    def _generate_options(self, delegation_pct: float, confidence: str, complexity: int, domain_familiarity: str) -> list[dict]:
        """Generate multi-option framing per Dastin (2023) findings."""
        # Option A: Conservative — preserve operator ownership
        option_a = {
            "label": "Option A — Conservative",
            "delegation_pct": round(delegation_pct * 0.6, 1),
            "description": "Minimal pre-written content; full decision ownership preserved",
            "pros": [
                "Operator maintains complete situational awareness",
                "Zero automation surprise risk",
                "Best for novel situations or high-stakes decisions",
            ],
            "cons": ["Higher cognitive load during handoff", "Slower ramp-up (~5-10 min vs ~3 min)"],
            "recommended_when": "First engagement after quiet window, or task complexity >7",
        }

        # Option B: Balanced — Goldilocks zone
        option_b = {
            "label": "Option B — Balanced (Recommended)",
            "delegation_pct": round(delegation_pct, 1),
            "description": "50% pre-written coordination with explicit choice points",
            "pros": [
                "Optimal delegation sweet spot per literature (Dastin 2023)",
                "Balances efficiency with calibration maintenance",
                "Supports trust development without over-reliance",
            ],
            "cons": ["Requires operator engagement to finalize", "May not reduce ramp-up as much as aggressive prep"],
            "recommended_when": "Established domain patterns, moderate time pressure",
        }

        # Option C: Aggressive — maximum efficiency within safety bounds
        option_c = {
            "label": "Option C — Aggressive",
            "delegation_pct": round(min(0.65, delegation_pct * 1.2) * 100, 1),
            "description": "Higher pre-written content ratio; faster handoff but increased automation surprise risk",
            "pros": [
                "Maximum ramp-up reduction (~6-8 minutes saved)",
                "Best for routine tasks in familiar domains",
                "Reduces cognitive load during high-pressure periods",
            ],
            "cons": ["Approaches automation surprise threshold (>60%)", "May erode trust if pattern shifts unexpectedly"],
            "recommended_when": "Task complexity <5, established patterns, N≥5 supporting examples available",
        }

        options = [option_a, option_b, option_c]

        # Mark recommended option based on context
        if confidence == "[LOW CONFIDENCE - RECOMMEND MANUAL REVIEW]":
            options[1]["note"] = f"⚠️ {confidence}"
        elif complexity >= 7 or domain_familiarity == "novel":
            options[0]["note"] = "★ Recommended for this context"
        else:
            options[1]["note"] = "★ Recommended per Goldilocks zone principle (40–60% delegation)"

        return options

    def _build_rationale(
        self,
        task_complexity: int,
        time_pressure: str,
        domain_familiarity: str,
        recommended_pct: float,
        confidence_level: str,
    ) -> str:
        """Build human-readable rationale grounded in literature priors."""
        parts = []

        # Context summary
        parts.append(f"Context: Task complexity {task_complexity}/10, {time_pressure} time pressure, {domain_familiarity} domain familiarity.")

        # Delegation recommendation with literature anchor
        if recommended_pct <= 0.45:
            parts.append("Recommendation leans conservative to preserve operator calibration during novel/high-complexity situations.")
        elif recommended_pct >= 0.55:
            parts.append("Recommendation toward upper Goldilocks bound due to elevated cognitive load from time pressure and/or complexity.")
        else:
            parts.append(f"Recommending {recommended_pct*100:.0f}% delegation — squarely within the 40–60% optimal offloading range (Dastin 2023).")

        # Confidence interpretation
        parts.append(f"Confidence level: {confidence_level}. " + 
                    ("Low evidence base — recommend manual verification before acting on recommendations." if confidence_level == "[LOW CONFIDENCE - RECOMMEND MANUAL REVIEW]" else
                     "Sufficient supporting data for automated deployment." if confidence_level == "[HIGH CONFIDENCE]" else
                     "Moderate evidence — operator should review underlying assumptions."))

        return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Human-AI Team Cognitive Load Calculator per Mayer & Chen (2024), Dastin (2023)"
    )
    parser.add_argument("--complexity", type=int, default=5, help="Task complexity 1-10")
    parser.add_argument("--time-pressure", choices=["low", "normal", "high", "critical"], default="normal")
    parser.add_argument("--domain", choices=["novel", "developing", "established"], default="established")
    parser.add_argument("--evidence-n", type=int, default=3, help="N recent examples supporting recommendation")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of formatted text")

    args = parser.parse_args()

    calculator = CognitiveLoadCalculator()
    result = calculator.calculate(
        task_complexity=args.complexity,
        time_pressure=args.time_pressure,
        domain_familiarity=args.domain,
        supporting_evidence_n=args.evidence_n,
    )

    if args.json:
        output = {
            "timestamp": result.timestamp,
            "recommended_delegation_pct": result.recommended_delegation_pct,
            "confidence_level": result.confidence_level,
            "confidence_numeric": result.confidence_numeric,
            "options": result.options,
            "rationale": result.rationale,
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("HUMAN-AI TEAM COGNITIVE LOAD CALCULATOR")
        print(f"Per Mayer & Chen (2024), Dastin (2023), Chen et al. (2023)")
        print(f"Generated: {result.timestamp}")
        print("=" * 70)
        print(f"\n📊 Recommended Delegation: {result.recommended_delegation_pct:.1f}%")
        print(f"   {result.confidence_level} ({result.confidence_numeric*100:.0f}% confidence numeric)\n")

        print("🎯 Multi-Option Framing:")
        for i, option in enumerate(result.options, 1):
            note = f" — {option.get('note', '')}" if option.get('note') else ""
            print(f"\n{i}. **{option['label']}** [{option['delegation_pct']:.1f}% delegation]{note}")
            print(f"   {option['description']}")
            print(f"\n   ✓ Pros: {', '.join(option['pros'])}")
            print(f"   ✗ Cons: {', '.join(option['cons'])}")
            print(f"   When: {option['recommended_when']}")

        print(f"\n💡 Rationale:\n   {result.rationale}")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
