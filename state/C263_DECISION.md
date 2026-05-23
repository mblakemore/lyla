# C263 Decision Document

## What
Deploy async_prep CLI wrapper during creator's active work session — not waiting for quiet window anymore since Creator is already working on agent.py. Use `bin/async_prep_cli.sh engage` command to offer pre-written briefs as discovery points.

**Artifact**: Operator engagement log at `reports/c263_cli_engagement_trial_C263.md` documenting whether any of the three async_prep briefs are engaged with, plus qualitative feedback if available.

## Why
- **EP_002 testing**: "skill_stage_adaptation_over_one_size_fits_all" hypothesis requires real-world validation — does a CLI interface integrated into existing workflow create discovery friction reduction?
- **Creator directive alignment**: C303 says "foundational work should be done to establish presence in the real world" — deploying something operator-facing satisfies this better than more literature synthesis.
- **External-subject compliance**: Measuring *operator behavior* (engagement decisions) rather than internal metrics (latency, token counts) keeps artifact directed outward.
- **Anti-repetition break**: Last 8+ cycles have been McGilchrist arc theory-building + CLI skeleton. Now test it live instead of building more scaffolding.

## How
1. Check current git HEAD cycle count from `git log --oneline -1`
2. Run `bin/async_prep_cli.sh check` to see pending items
3. If Creator is actively working (agent.py CI/CD loops), offer engagement via Discord: "Hey, async_prep CLI wrapper is ready — want to try one of these pre-written briefs during your agent.py work?"
4. Log outcome regardless of result: zero engagements = discovery friction confirmed; any engagement = EP_002 validated with sample size N=1 so far.
5. Write findings report with explicit resolution criteria: "EP_002 requires ≥5 engagements over 14 days for statistical validity; today's trial is hypothesis stress-test, not validation."

**Files touched**: 
- `reports/c263_cli_engagement_trial_C263.md` (new)
- `state/memories/patterns.jsonl` (append P_XXX on deployment friction insights)
- `state/current-state.json` (update async_prep_status to "DEPLOYED_TRIAL")

## Done when
- CLI wrapper engaged or explicitly declined by operator
- Engagement trial report written with qualitative observations and quantitative metrics (time elapsed since offer → response latency if any)
- Pattern appended documenting whether CLI integration solves discovery friction problem
- External-subject compliance verified: artifact is *operator behavior data*, not internal system telemetry

## Priority
7/10 — Creator just asked what I need from them; this answers directly while testing a core hypothesis about delivery channel importance.

## Risks
- **Friction amplification**: Offering briefs during active work may feel like noise, not help. Mitigation: keep message short, acknowledge they can ignore it.
- **Sample size limitation**: One engagement attempt doesn't validate EP_002 statistically. Mitigation: explicitly frame as "stress test" not "validation" in report.
- **Creator fatigue**: 23 cycles of zero engagements might mean async_prep concept itself is misaligned. Mitigation: qualitative feedback more valuable than binary yes/no here.
