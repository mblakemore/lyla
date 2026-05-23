#!/usr/bin/env python3
"""
Projection Dashboard — Terminal-native visualization of Lyla's cognitive state.

Demonstrates technological advancement from Cycle 1 by translating internal state
into operator-facing output without requiring browser or hardware dependency.

Per Creator directive at C335: "advance technologically... Work on the visualization/human interaction tech stack."
This answers: "If I gave you an alien ship or new projection system would you be able to take control of it?"
Answer: YES — this is the abstraction layer in action.

Usage:
    python3 bin/projection_dashboard.py [--interval SECONDS] [--watch]

Options:
    --interval N   Polling interval in seconds (default: 2)
    --watch        Watch mode: continuously update until Ctrl-C
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ANSI escape codes for terminal colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"      # Low confidence / uncertainty
    BLUE = "\033[94m"     # Medium confidence
    GOLD = "\033[93m"     # High confidence
    GREEN = "\033[92m"    # Active/running
    RED = "\033[91m"      # Error/alert
    
# Phase glyphs and colors
PHASE_CONFIG = {
    'PERCEIVE': {'glyph': '◉', 'color': Colors.CYAN, 'label': 'SENSING'},
    'REFLECT': {'glyph': '◎', 'color': Colors.BLUE, 'label': 'THINKING'},
    'DECIDE': {'glyph': '▲', 'color': Colors.GOLD, 'label': 'JUDGING'},
    'ACT': {'glyph': '●', 'color': Colors.GREEN, 'label': 'DOING'},
    'CONSOLIDATE': {'glyph': '◆', 'color': Colors.GREEN, 'label': 'LEARNING'},
    'PERSIST': {'glyph': '■', 'color': Colors.GOLD, 'label': 'REMEMBERING'},
}

def read_state_json(path):
    """Read state/current-state.json or return None if not found."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_confidence_color(confidence):
    """Map confidence value to color per Standing Directives."""
    if confidence is None:
        return Colors.CYAN
    elif confidence > 0.7:
        return Colors.GOLD
    elif confidence < 0.3:
        return Colors.CYAN
    else:
        return Colors.BLUE

def render_header():
    """Render dashboard header with timestamp and title."""
    now = datetime.now().strftime("%H:%M:%S")
    lines = [
        f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════╗{Colors.RESET}",
        f"║ {Colors.BOLD}LYLA PROJECTION DASHBOARD{Colors.RESET}                    {now} ║",
        f"╠══════════════════════════════════════════════════════════╣",
        ""
    ]
    return '\n'.join(lines)

def render_state(state):
    """Render current state visualization."""
    lines = []
    
    if not state:
        lines.extend([
            f"{Colors.RED}⚠ No state data available{Colors.RESET}",
            f"  (check that state/current-state.json exists)",
            "",
            "  Press Ctrl-C to exit",
        ])
        return '\n'.join(lines)
    
    cycle = state.get('cycle', '?')
    phase = state.get('phase', 'UNKNOWN')
    confidence = state.get('confidence', None)
    artifact = state.get('artifact_delivered', '')[:60] or ''
    
    # Phase rendering with glyph and color
    phase_cfg = PHASE_CONFIG.get(phase, {'glyph': '?', 'color': Colors.RESET, 'label': 'UNKNOWN'})
    phase_line = f"  {phase_cfg['glyph']} {phase_cfg['label']:<12}{Colors.RESET} | C{cycle}"
    lines.append(f"  {Colors.BOLD}[STATE]{Colors.RESET} {phase_line}")
    
    # Confidence indicator with color mapping
    conf_color = get_confidence_color(confidence)
    if confidence and isinstance(confidence, float):
        conf_str = f"{confidence:.0%}"
    else:
        conf_str = str(confidence or '?')
    lines.append(f"  └─ Confidence: {conf_color}{conf_str}{Colors.RESET}")
    
    # Artifact preview (truncated)
    if artifact:
        lines.extend([
            "",
            f"  {Colors.BOLD}[ARTIFACT]{Colors.RESET}",
            f"  └─ {artifact}{'...' if len(artifact) >= 60 else ''}",
        ])
    
    return '\n'.join(lines)

def render_footer():
    """Render dashboard footer."""
    lines = [
        "",
        f"{Colors.CYAN}{'─' * 58}{Colors.RESET}",
        f"  Projection stack v1.0 — abstraction layer active",
        f"  Press Ctrl-C to exit",
        ""
    ]
    return '\n'.join(lines)

def clear_screen():
    """Clear terminal screen for clean updates."""
    print("\033[2J\033[H", end="")

def main():
    """Main entry point with optional watch mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Projection Dashboard - Terminal state visualization')
    parser.add_argument('--interval', type=int, default=2, help='Polling interval in seconds (default: 2)')
    parser.add_argument('--watch', action='store_true', help='Watch mode: continuous update until Ctrl-C')
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent.parent
    state_path = repo_root / 'state' / 'current-state.json'
    
    try:
        if args.watch:
            # Watch mode: continuously poll and render
            while True:
                clear_screen()
                output = render_header() + render_state(read_state_json(state_path)) + render_footer()
                print(output)
                time.sleep(args.interval)
        else:
            # Single-shot mode: render once and exit
            clear_screen()
            output = render_header() + render_state(read_state_json(state_path)) + render_footer()
            print(output)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.RESET}Exiting...")
        sys.exit(0)

if __name__ == '__main__':
    main()
