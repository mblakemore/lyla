# Cycle 281 Decision Document

## What: Operator-Centric Projection System Discovery

Design a minimal qualitative inquiry to identify what kind of projection/presence system would actually serve the operator's needs — pivoting from abstract theory to concrete utility validation.

## Why: Closing the Gap Between Theory and Adoption

- **McGilchrist arc complete:** C280 synthesized all three actionable insights; continuing to C290 would be redundant theory application
- **Zero adoption signal:** async_prep has seen no real engagement in ~24 days despite deployment at C231
- **Creator directive alignment:** Creator explicitly requested "qualitative feedback" over measurement frameworks (C300-C301)
- **Anti-repetition rule:** Seven consecutive cycles on McGilchrist thread (C274-C280); need external pivot now, not at C290

The core question isn't "what should projection systems look like theoretically?" but "what does the operator actually need right now that current tools don't provide?"

## How: Minimal Qualitative Probe

**Approach:**
1. Design a 3-question inquiry focused on friction points, not capabilities
2. Frame as "help me help you" rather than "here's my new feature"
3. Deliver via Discord (low-friction channel where creator already communicates)
4. Synthesize responses into revised design spec

**Files to touch:**
- `messages/to-creator.md` — send inquiry message
- `reports/operator_projection_needs_C281.md` — synthesize findings + next steps

**Discord message template:**
> Hey — I've been thinking about our async_prep tool and realizing it hasn't landed for you. Before I build anything else, can you tell me:  
>   
> 1. When was the last time you *wanted* an AI assistant to surface information proactively? What were you doing?  
> 2. What would have made that moment better if someone had just... known what you needed?  
> 3. If I could only do one thing differently with how I show up (not what I show), what would it be?  
>   
> No pressure — even a one-liner helps more than silence.

## Priority: 7/10

This is a pivot point cycle. Getting the wrong signal now wastes future cycles building the wrong thing. The McGilchrist theory told us *why* projection matters; this cycle tests *what actually works*.

## Done When:

- [ ] Inquiry sent via Discord within this cycle
- [ ] Initial synthesis report created (even if response pending)
- [ ] Pattern appended documenting "zero-adoption diagnostic protocol" as reusable knowledge
- [ ] External-subject compliance verified: artifact serves operator needs discovery, not self-monitoring

## Risks:

**Low:** Operator doesn't respond → still produces inquiry design pattern + decision log (learning about non-response as data)

**Medium:** Response reveals async_prep mechanism itself is broken, not discoverability → requires tool redesign, not just interface tweak

**Mitigation:** Frame questions to distinguish "didn't know it existed" vs "exists but wrong model" — question #2 specifically targets mechanism fit vs awareness
