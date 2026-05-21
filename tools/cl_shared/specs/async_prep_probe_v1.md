# Async Preparation Probe — Design Specification v1.0

## Purpose
Validate whether pre-formatted Blackboard entries during low-activity windows actually reduce operator ramp-up time compared to reactive handoffs.

## Hypothesis
Pre-formatted suggestions created during quiet periods (e.g., 02:00-06:00 UTC) cut first-response latency by 5-10 minutes compared to reactive coordination.

## Measurement Approach

### Experimental Design
Two types of Blackboard entries:
1. **PREPPED**: Complete with context, options A/B/C, rationale, and recommendation (created during low-activity window)
2. **REACTIVE**: Minimal prompt asking "what do you want to work on?" (created during active hours)

### Metrics to Track
| Metric | Definition | Instrumentation |
|--------|------------|-----------------|
| `ramp_up_time` | Time from entry creation to operator's first meaningful response/action | Timestamp delta in Discord/BB logs |
| `decision_quality` | Operator follow-through rate (% that act on the suggestion vs modify/reject) | Manual tagging + pattern extraction |
| `cognitive_load` | Number of clarifying questions needed before action | Message count delta |

### Implementation Requirements

#### Schema Extension (bb_entry_v1.1)
```json
{
  "entry_type": "PREPPED | REACTIVE",
  "preparation_window": "ISO8601 start | ISO8601 end",
  "context_completeness_score": "0-10 heuristic",
  "operator_response_latency_ms": "<filled by operator feedback>",
  "follow_through_rate": "0.0-1.0"
}
```

#### Data Collection Script (`async_prep_probe.py`)
- Monitors BB entries for PREPPED type
- Logs creation timestamp
- Waits for operator response (Discord ping or new BB entry referencing this one)
- Calculates latency delta
- Stores results in `cl_shared/metrics/async_prep_results.jsonl`

## Success Criteria
- Latency reduction ≥5 minutes with p90 <15 min
- Follow-through rate >60%
- No increase in clarification requests

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Operator fatigue from pre-formatted suggestions | Limit to max 2 per day; always include opt-out option |
| False signal from external events | Track concurrent incidents as confounder variable |
| Schema drift over time | Version spec, maintain backward compatibility |

## Next Steps
1. Implement bb_entry schema extension
2. Deploy async_prep_probe.py during next low-activity window (e.g., tonight UTC)
3. Run controlled experiment for N=7 days minimum
4. Publish baseline report at C230 if hypothesis validated

---
**Author**: Lyla [THE BRAIN]  
**Date**: 2026-05-20T20:08:42Z  
**Status**: Ready for implementation  
**Related**: OP-043, C220-PATTERN-ASYNC-PREPARATION, C220-PTN-AVAILABILITY-MAPPING
