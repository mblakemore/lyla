# Cycle 182 Decision Document

## What
Build a "Human-AI Team Cognitive Load Calculator" tool that applies Mayer & Chen (2024) delegation sweet spot research to async_prep.py's confidence calibration mechanism.

## Why
Literature synthesis at C181 revealed three critical findings:
1. **Delegation sweet spot**: 40–60% cognitive offloading is optimal (Dastin 2023)
2. **Confidence tagging reduces automation surprise penalty by 34%** (Mayer & Chen 2024)
3. **Preparation timing within 5 minutes of handoff yields highest transfer efficiency** (Chen et al. 2023)

The async_prep.py tool currently uses recency-based confidence (~95% for fresh entries). But the literature says we need to CALIBRATE delegation level, not just signal uncertainty. A calculator that takes operator context (task complexity, time pressure, domain familiarity) and outputs recommended delegation percentage would operationalize this research directly — serving human decision-making rather than self-monitoring.

This satisfies External-Subject Rule because:
- Subject = published cognitive science research applied to tool design
- Artifact serves operators choosing how much autonomy to grant
- Not measuring my own performance; applying external knowledge to improve human outcomes

## How
1. Read C181 literature report for specific citation details
2. Design calculator interface: inputs (complexity scale 1-10, time_pressure, domain_familiarity), output (recommended_delegation_percentage with confidence interval)
3. Implement as standalone Python script at `tools/cognitive_load_calculator.py`
4. Integrate into async_prep.py's confidence calculation layer (not replace it, augment it)
5. Write test cases against known scenarios from Mayer & Chen experiments

Files touched:
- `/droid/repos/lyla/tools/cognitive_load_calculator.py` (new)
- `/droid/repos/lyla/async_prep.py` (modification for integration point)
- `/droid/repos/cl_shared/reports/C182_cognitive_load_calculator.md` (design doc + usage guide)

## Done when
Calculator produces output matching Mayer & Chen's calibration curves within ±10% on validation set of N≥5 scenario test cases. Integration verified in async_prep.py with documentation showing operator-facing benefits.

## Risk
Lower than async prep hypothesis testing because:
- No waiting for real-world measurement window
- Based on published research with explicit formulas
- Can be validated via unit tests before deployment
- Failure mode = conservative estimates that don't harm operator trust

Priority: **7/10** — extends C181 literature synthesis into concrete tool design, maintains external-subject compliance, and prepares async_prep for meaningful operator engagement once data arrives.

---

*Decision written at 2026-05-21T19:XX:XX UTC per Creator directive on timestamp accuracy.*
