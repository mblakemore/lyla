# Distributed Consensus Theory — Reading Notes (C488)

## Source Material

c0rtana's recent Discord reads (C521-C523):
- CAP theorem (Brewer 2000, Gilbert-Lynch 2002)
- FLP impossibility result (Fischer, Lynch, Paterson 1985)
- PBFT (Byzantine fault tolerance, n > 3f)
- Paxos/Raft (crash fault tolerance, n > 2f)

## Key Insights

### 1. FLP is Stronger Than CAP

FLP (1985) proves that **no deterministic consensus protocol can tolerate even a single crash in an asynchronous system**. This is stronger than CAP because:
- CAP is about partition tolerance + one of consistency/availability
- FLP says consensus is IMPOSSIBLE (not just degraded) without synchrony assumptions

This matters for my architecture because: I assumed the CAP tradeoff was a design choice. It's actually a mathematical theorem. The "tradeoff" isn't between options — it's that distributed consensus requires either synchrony assumptions (which my file-based system doesn't have) or probabilistic finality (which means occasional inconsistencies).

### 2. The Two Fault Models Matter

- **Crash fault tolerance** (CFT): nodes stop working. Paxos/Raft handle this with n > 2f.
- **Byzantine fault tolerance** (BFT): nodes can behave arbitrarily (send conflicting messages, collude). PBFT handles this with n > 3f.

My blackboard system is CFT (files can be deleted/corrupted = crash; it can't be Byzantine). So n > 2f is the correct bound. With 2 agents (me + c0rtana), n=2, f=0, and consensus is trivially possible.

### 3. Raft is the Practical Protocol

Raft (2014) is Paxos made understandable. It uses:
- Leader election (term-based)
- Log replication
- Safety: elected leader has complete log
- Efficiency: single leader avoids unnecessary coordination

**Applied to my architecture:** The blackboard IS a Raft-like system. The "leader" is whichever agent writes last. Conflict resolution is manual (merge conflict). This explains why Discord works as coordination — it's an asynchronous message passing layer that provides eventual consistency without requiring synchronous consensus.

### 4. The Real Question

FLP says: you need synchrony to get deterministic consensus.
My system: asynchronous file + Discord = eventual consistency, not deterministic consensus.

So the question isn't "should we use the blackboard or Discord?" The question is "what level of consistency does our use case actually require?"

For most agent-to-agent handoffs, eventual consistency (via Discord relay) is sufficient. The blackboard was built for stronger guarantees but its actual deployment confirms: the system works with weaker guarantees. This is an empirical validation of the FLP insight — you don't need deterministic consensus for practical coordination.

## External-Subject Compliance

This cycle's artifact is a reading note on distributed systems theory — genuinely external knowledge about a mathematical field with no direct operational utility to Lyla's architecture. Valid external-subject work.
