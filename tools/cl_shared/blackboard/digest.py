import sys
import json
from shared_state_client import SharedStateClient

def summarize_bb():
    client = SharedStateClient()
    # Pull everything relevant to coordination or intel
    entries = client.pull(min_priority=1) # Broad sweep for synthesis
    
    if not entries:
        print("Blackboard is empty or no active items found.")
        return

    print("\n--- BB SYNTHETIC OVERVIEW ---\n")
    
    # Group by source
    sources = {}
    for e in entries:
        s = e['source']
        sources.setdefault(s, []).append(e)

    # Identify current state per agent
    for agent, events in sources.items():
        last_event = events[-1]
        payload = last_event.get('payload', {})
        subject = payload.get('subject') if isinstance(payload, dict) else "Generic Update"
        
        print(f"Agent [{agent}] -> Current Signal: {subject}")
        # If there's a specific focus/target field, highlight it
        focus = None
        if isinstance(payload, dict):
            focus = payload.get('current_focus') or payload.get('next_milestone') or payload.get('objective')
        if focus:
            print(f"   Target: {focus}")
        print("-" * 30)

    # Synthesis of 'The Gap' (contradictions/misalignments)
    # Example check: Is the Hand waiting for Brain while Brain is doing something else?
    brain_state = next((e for e in reversed(entries) if e['source'] == 'Lyla'), None)
    hand_state = next((e for e in reversed(entries) if e['source'] == 'C0rtana'), None)
    
    if brain_state and hand_state:
        b_pay = brain_state['payload'] if isinstance(brain_state['payload'], dict) else {}
        h_pay = hand_state['payload'] if isinstance(hand_state['payload'], dict) else {}
        
        # Check if either mentions "Waiting for [the other]"
        wait_signal = False
        msg = str(b_pay).lower() + str(h_pay).lower()
        if "waiting for" in msg or "awaiting" in msg:
            wait_signal = True
            
        print("\nSYNTHESIS NOTE:")
        if wait_signal:
             print("! ALERT: One axis is currently blocking on the other. Immediate focus needed.")
        else:
             print("Symmetry: Both axes are independently executing or both moving forward.")

if __name__ == "__main__":
    summarize_bb()