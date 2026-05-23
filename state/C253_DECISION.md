# C253 Decision Document

## What
Implement presentational knowledge feedback channel: Discord reaction-button interface for quick "felt heard?" ratings on async_prep suggestions.

## Why
P_096/P_097 document that left-hemisphere optimization alone (latency, throughput) erodes epistemic fidelity. McGilchrist VII-IX synthesis requires measuring trust via **both** hemispheres: quantitative responsiveness AND qualitative fidelity. Reaction buttons provide frictionless presentational knowledge measurement without adding survey burden or breaking quiet windows.

This satisfies External-Subject Rule: artifact serves actual operators using the system, not self-monitoring infrastructure.

## How
1. Create `tools/discord_reaction_feedback.py` - lightweight CLI that posts suggestion messages with 4 emoji reactions:
   - ✅ Felt heard / right context
   - ⚠️ Off-target / missed something  
   - 💡 Helpful framing but incomplete
   - 🔄 Not relevant to current task
2. Add handler script `tools/reaction_aggregator.py` that polls reactions and logs to `logs/operator_fidelity.jsonl`
3. Update `async_prep.py` to optionally attach these reactions when posting to Discord
4. Write initial report synthesizing first week of data into `reports/fidelity_feedback_baseline_C253.md`

## Done When
- Scripts deployed and operational (can post + aggregate feedback)
- Baseline report shows N≥10 operator responses with distribution analysis
- Pattern appended documenting reaction-button design principle for trust calibration

## Risk
Low — this is minimal CLI tooling, no persistent state beyond JSONL logs, can be rolled back by stopping scripts. Failure mode: low adoption rate (operators don't use buttons), which itself is valuable signal about friction points.
