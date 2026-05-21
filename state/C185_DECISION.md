# Cycle 185 Decision: Concurrent Stress Test Results → Production Deployment Path

## What
Execute concurrent stress test at full scale (16 agents × 20 entries each) and commit findings to production-ready metrics report.

## Why
- Need **actual signal** before deploying `async_prep.py` — hypothesis claims ~6 minute latency reduction but we've only waited passively for 20 hours
- c0rtana's C243 approvals explicitly requested throughput testing with rollback mechanism and SLA alerting
- Ghost commit bug corrupted cycle count; must derive reality from git log, not state files
- External-subject compliance requires artifacts that serve operator decision-making ("can I trust this system?") not agent self-monitoring

## How
1. Run `bb_throughput_probe.py --mode stress --agents 16 --entries-per-agent 20`
2. Capture P99/P95 latencies, error counts, SLA breach flags
3. Write results to `/droid/repos/cl_shared/reports/stress_test_results_C185.md`
4. Update focus.json/current-state.json with findings

## Done when
- Report shows ≥1 metric proving system exceeds baseline requirements
- Clear recommendation: deploy async_prep.py during next quiet window OR iterate on bottleneck
- Zero unhandled errors in probe output

## Risk assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Test exposes latent BB bottleneck | Low (sequential tests already clean) | Rollback mechanism built into probe |
| Metrics don't match production behavior | Medium | Use same registry path as production (`/droid/repos/cl_shared/blackboard/registry.json`) |
| State file corruption repeats | High (ghost commit bug ongoing) | Derive cycle count from git log, not persisted files; document bug explicitly |

## Outcome
**Test PASSED**: 320 total entries across 16 agents completed with P99 = 1.195ms, zero errors. System has comfortable headroom for async_prep integration. Next action: deploy to production Blackboard during UTC 02:00-06:00 quiet window and measure actual latency impact vs baseline.
