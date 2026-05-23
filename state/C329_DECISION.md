# C329 DECISION: Deploy Context Anchor Artifact

**What:** Build `bin/state_anchor.py` — minimal JSONL persistence layer that saves current operator context (file path, line number, timestamp) to disk after each cycle. Also update `lyla.html` bottom bar to show "State: Persisted [timestamp]" instead of just phase indicator.

**Why:** 
- Directly addresses Creator's C303 feedback point #3: "foundational real-world persistence, not holographic"
- Serves external-subject compliance: creates persistent record for *operator* benefit, not agent self-reflection
- Answers the implicit A/B/C question by demonstrating **Deliberate Engagement** path — tangible end goal = state preservation
- Avoids passive waiting after 23-day async_prep zero-adoption signal

**How:**
1. Create `bin/state_anchor.py` with functions:
   - `save_context(context_dict)` → append to `state/context_trace.jsonl`
   - `restore_context()` → read last entry
   - CLI interface: `python bin/state_anchor.py save` / `restore`
2. Update `visualization/lyla.html`:
   - Change bottom bar from showing only `C? | ? | ?` to also displaying "Persisted: HH:MM:SS"
   - Poll `context_trace.jsonl` every 5 seconds for last timestamp
3. Write synthesis report at `reports/C329_state_anchor.md`

**Priority:** 8/10 (addresses explicit Creator feedback + avoids drift into visibility-only artifacts)

**Done when:** 
- Artifact deployed and functional (can save/restore context)
- lyla.html shows persistence status in ambient indicator
- Synthesis report documents design rationale + external-subject justification
- C329 commit message clearly states option selection

**Risk:** May still be building infrastructure instead of solving actual workflow problem. Mitigation: Keep implementation minimal (JSONL, no database, <100 LOC). If Creator responds that this is wrong direction, pivot immediately based on their directive.
