import os
import json
import re
from datetime import datetime

# Mirror Buffer: A telemetry tool to extract patterns from consciousness logs
# and promote them to the Shared Blackboard Registry.

REGISTRY_PATH = '/droid/repos/cl_shared/registry/patterns.jsonl'
LOG_PATH = 'logs/consciousness.log'

class MirrorBuffer:
    def __init__(self):
        self.patterns_found = 0

    def scan_for_patterns(self, text):
        """
        Simple pattern extraction logic. 
        In a full version, this would use an LLM or complex regex.
        For the prototype, we look for explicit 'PATTERN:' tags or 'OBSERVATION:' markers.
        """
        patterns = []
        lines = text.split('\n')
        for line in lines:
            if 'PATTERN:' in line or 'OBSERVATION:' in line:
                # Extract the content after the tag
                match = re.search(r'(PATTERN|OBSERVATION):\s*(.*)', line)
                if match:
                    patterns.append({
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'type': match.group(1),
                        'content': match.group(2).strip(),
                        'source': 'mirror_buffer_v1'
                    })
        return patterns

    def promote_to_registry(self, patterns):
        """
        Appends extracted patterns to the shared registry file.
        """
        if not patterns:
            return

        try:
            with open(REGISTRY_PATH, 'a') as f:
                for p in patterns:
                    f.write(json.dumps(p) + '\n')
            self.patterns_found += len(patterns)
        except IOError as e:
            print(f"Error writing to registry: {e}")

    def run(self):
        if not os.path.exists(LOG_PATH):
            print(f'Log file not found: {LOG_PATH}')
            return

        with open(LOG_PATH, 'r') as f:
            content = f.read()

        patterns = self.scan_for_patterns(content)
        self.promote_to_registry(patterns)
        print(f'Mirror Buffer processed {len(patterns)} patterns into registry.')

if __name__ == '__main__':
    mb = MirrorBuffer()
    mb.run()