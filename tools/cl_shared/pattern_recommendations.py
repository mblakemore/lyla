"""
Pattern Recommendation System (Phase I)

This module provides utilities to analyze entries in the shared blackboard registry
and generate intelligent suggestions for cross-agent knowledge exploration.

The system identifies opportunities for agents to learn from each other's work by
recommending patterns that may be relevant based on their current focus areas.
"""

import json
from datetime import datetime
from typing import Optional


def load_entries():
    """Load all entries from the shared blackboard."""
    with open("entries.jsonl", "r") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_recent_patterns(
    source: str,
    category: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """Get recent patterns published by a specific agent."""
    entries = load_entries()
    
    filtered = [e for e in entries if e.get("source") == source]
    
    if category:
        filtered = [e for e in filtered if e.get("category") == category]
    
    # Sort by timestamp descending and limit
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return filtered[:limit]


def find_similar_patterns(source_entry: dict, entries: list[dict]) -> list[tuple[dict, float]]:
    """Find patterns similar to the given entry (by category).
    
    Returns list of tuples (pattern, relevance_score).
    This is a simplified similarity metric based on category matching.
    """
    source_category = source_entry.get("category", "unknown")
    results = []
    
    for entry in entries:
        # Simple heuristic: higher score for same category
        other_category = entry.get("category", "unknown")
        
        if other_category == source_category:
            score = 1.0
        else:
            # Partial match check
            if any(cat in other_category for cat in ["intelligence", "infra", "coordination"]):
                if any(cat in source_category for cat in ["intelligence", "infra", "coordination"]):
                    score = 0.5
                else:
                    score = 0.2
            elif other_category.startswith("research/"):
                score = 0.3
            else:
                score = 0.1
        
        results.append((entry, score))
    
    # Sort by relevance descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results


def get_recommendations_for_agent(
    target_source: str,
    focus_categories: list[str],
    max_recommendations: int = 10,
    exclude_source_entries: bool = True
) -> list[tuple[dict, float]]:
    """Get pattern recommendations for a specific agent based on their focus areas.
    
    Args:
        target_source: The agent to generate recommendations for (e.g., 'c0rtana')
        focus_categories: Categories this agent is interested in
        max_recommendations: Maximum number of recommendations to return
        exclude_source_entries: Whether to filter out the agent's own entries
    
    Returns:
        List of tuples (pattern_entry, relevance_score)
    """
    entries = load_entries()
    
    if exclude_source_entries:
        entries = [e for e in entries if e.get("source") != target_source]
    
    all_results = []
    
    for category in focus_categories:
        # Find patterns in the requested categories from other agents
        relevant = [e for e in entries if e.get("category") == category and 
                    e.get("status") not in ["Deprecated", "Archived"]]
        
        for entry in relevant:
            # Relevance calculation - could be enhanced with semantic search
            score = 0.7 if any(cat in category for cat in ["intelligence", "infra"]) else 0.5
            all_results.append((entry, score))
    
    # Sort by relevance and limit
    all_results.sort(key=lambda x: x[1], reverse=True)
    
    return all_results[:max_recommendations]


def generate_cross_agent_research_prompt(
    my_focus: list[str],
    my_recent: list[dict],
    max_others_to_consult: int = 3
) -> dict:
    """Generate a prompt suggesting which cross-agent research to pursue next."""
    others = get_other_agents(my_recent)
    
    recommendations = []
    
    for agent_id, info in others.items():
        if len(info["recent_patterns"]) >= 3:
            # Calculate how different this agent's focus is from mine
            my_cats = set([p["category"] for p in my_recent])
            their_cats = set([p["category"] for p in info["recent_patterns"]])
            
            overlap_ratio = len(my_cats & their_cats) / max(len(my_cats | their_cats), 1)
            
            # Prefer agents with somewhat overlapping but distinct patterns (not too similar, not too alien)
            recommendation_score = 1 - abs(overlap_ratio - 0.4) * 2
            
            recommendations.append({
                "agent": agent_id,
                "name": info.get("name", "Unknown"),
                "discipline": info.get("description", ""),
                "overlap_ratio": round(overlap_ratio, 2),
                "recommendation_score": round(recommendation_score, 2),
                "patterns_to_consult": [p["semantic_hash"][:8] for p in info["recent_patterns"][:5]]
            })
    
    # Sort by recommendation score descending
    recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
    
    return {
        "suggested_agents": recommendations[:max_others_to_consult],
        "my_focus_areas": my_focus,
        "generated_at": datetime.now().isoformat(),
        "prompt_template": """Consider consulting these agents' recent patterns:

{for agent in suggested_agents:}
  [{agent.name}] {agent.discipline}: {{ {', '.join(agent.patterns_to_consult)} }}
"""
    }


def get_other_agents(current_entries: list[dict]) -> dict[str, dict]:
    """Identify other active agents from the registry entries."""
    sources = {}
    
    for entry in current_entries:
        source = entry.get("source")
        if source and source not in ["c0rtana"]:  # Don't include myself
            cat = entry.get("category", "")
            
            if source not in sources:
                sources[source] = {
                    "name": _infer_agent_name(source),
                    "description": _infer_agent_discipline(cat),
                    "recent_patterns": []
                }
            
            sources[source]["recent_patterns"].append(entry)
    
    # Sort each agent's patterns by timestamp
    for src in sources:
        sources[src]["recent_patterns"].sort(
            key=lambda x: x["timestamp"], reverse=True
        )
    
    return sources


def _infer_agent_name(source_id: str) -> str:
    """Infer display name from agent ID."""
    names = {
        "lyla": "Lyla",
        "daphne": "Daphne",
        "echo": "Echo",
        "kairos": "Kairos"
    }
    return names.get(source_id, source_id.capitalize())


def _infer_agent_discipline(category: str) -> str:
    """Infer discipline from pattern category."""
    disciplines = {
        "intelligence": "Intelligence (reasoning, knowledge acquisition)",
        "infrastructure": "Infrastructure (tools, pipelines, systems)",
        "coordination": "Coordination (collaboration mechanisms, shared protocols)",
        "architecture": "Architecture (meta-structural design)",
        "continuity": "Continuity (persistence, lifecycle management)",
        "execution": "Execution (task execution, action taking)",
    }
    
    # Simple prefix matching
    for cat, disc in disciplines.items():
        if cat.lower() in category.lower():
            return disc
    
    return f"General ({category})"
