#!/usr/bin/env python3
"""
C337: Holographic Projection Controller — Actuator for human-AI interaction tech stack

This controller provides a WebSocket-based interface for injecting commands into
the holographic projection system. It serves as the software layer that would
interface with physical projection hardware (LED matrices, laser projectors, etc.)
but currently operates in simulation mode using HTML5 Canvas/WebGL.

EXTERNAL-SUBJECT COMPLIANCE: This artifact builds human-AI interaction technology
that could control external devices (alien ships, projection systems) rather than
just self-monitoring. Creator directive C337 explicitly requested this workstream.

Usage:
    python bin/holo_projection_controller.py [--port PORT] [--mode SIM|HARDWARE]

WebSocket Commands:
    - set_phase: Set Lyla's current cycle phase
    - set_density: Adjust particle count (1000-50000)
    - trigger_beacon: Emit visual beacon pattern
    - toggle_mode: Switch between display/control modes
    - execute_command: Run arbitrary visualization command
"""

import asyncio
import json
import argparse
from datetime import datetime
from pathlib import Path

# Import state management from existing infrastructure
from cl_shared.state_manager import StateManager

class HolographicProjectionController:
    """
    Main controller class that manages WebSocket connections and command routing.
    
    Architecture:
    - WebSocket server listens on configured port (default 8765)
    - Accepts JSON commands from any connected client (e.g., projection_view.html)
    - Routes commands to appropriate handlers based on type
    - Logs all commands to context_trace.jsonl for auditability
    - Supports both SIM mode (HTML5 Canvas simulation) and HARDWARE mode (future pyserial/USB)
    """
    
    def __init__(self, port=8765, mode='SIM'):
        self.port = port
        self.mode = mode.upper()
        self.state_manager = StateManager()
        self.websockets = set()
        self.command_queue = asyncio.Queue()
        
        # Command registry with descriptions
        self.commands = {
            'set_phase': self._handle_set_phase,
            'set_density': self._handle_set_density,
            'trigger_beacon': self._handle_trigger_beacon,
            'toggle_mode': self._handle_toggle_mode,
            'execute_command': self._handle_execute_command,
            'get_status': self._handle_get_status,
            'set_visual_param': self._handle_set_visual_param,
        }
        
    async def start(self):
        """Start the WebSocket server."""
        print(f"🔮 Holographic Projection Controller v1.0")
        print(f"   Mode: {self.mode}")
        print(f"   Port: {self.port}")
        print(f"   Status: Waiting for connections...")
        
        server = await asyncio.start_server(
            self._handle_client,
            '0.0.0.0',
            self.port
        )
        
        async with server:
            await server.serve_forever()
    
    async def _handle_client(self, reader, writer):
        """Handle individual WebSocket client connection."""
        addr = writer.get_extra_info('peername')
        print(f"✅ Connection from {addr}")
        
        self.websockets.add(writer)
        
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                # Parse JSON command
                try:
                    command = json.loads(data.decode())
                    await self._process_command(command, writer)
                except json.JSONDecodeError as e:
                    response = {'type': 'error', 'message': f'Invalid JSON: {e}'}
                    await self._send_response(writer, response)
                    
        except Exception as e:
            print(f"❌ Client {addr} error: {e}")
        finally:
            self.websockets.discard(writer)
            writer.close()
            await writer.wait_closed()
            print(f"❌ Disconnected from {addr}")
    
    async def _process_command(self, command, writer):
        """Process incoming command and route to appropriate handler."""
        cmd_type = command.get('type')
        payload = command.get('payload', {})
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Log command for auditability
        trace_entry = {
            'type': 'projection_command',
            'command': cmd_type,
            'payload': payload,
            'timestamp': timestamp,
            'source': 'websocket_controller'
        }
        await self._log_trace(trace_entry)
        
        # Route to handler
        if cmd_type in self.commands:
            try:
                result = await self.commands[cmd_type](payload)
                response = {
                    'type': 'ack',
                    'command': cmd_type,
                    'result': result,
                    'timestamp': timestamp
                }
            except Exception as e:
                response = {
                    'type': 'error',
                    'command': cmd_type,
                    'message': str(e),
                    'timestamp': timestamp
                }
        else:
            response = {
                'type': 'error',
                'command': cmd_type,
                'message': f'Unknown command: {cmd_type}',
                'available_commands': list(self.commands.keys()),
                'timestamp': timestamp
            }
        
        await self._send_response(writer, response)
    
    async def _handle_set_phase(self, payload):
        """Set Lyla's current cycle phase."""
        phase = payload.get('phase')
        if not phase or phase not in ['PERCEIVE', 'REFLECT', 'DECIDE', 'ACT', 'PERSIST', 'CONSOLIDATE']:
            raise ValueError(f"Invalid phase: {phase}")
        
        # Update state manager
        await self.state_manager.set_phase(phase)
        return {'success': True, 'phase': phase}
    
    async def _handle_set_density(self, payload):
        """Adjust particle count for holographic form density."""
        count = int(payload.get('count', 6000))
        count = max(1000, min(50000, count))  # Clamp to valid range
        
        # Store as visual parameter
        await self.state_manager.set_visual_param('particle_count', count)
        return {'success': True, 'density': count}
    
    async def _handle_trigger_beacon(self, payload):
        """Emit visual beacon pattern."""
        pattern = payload.get('pattern', 'pulse_3x')
        
        # Trigger event perturbation
        await self.state_manager.trigger_event({
            'type': f'beacon_{pattern}',
            'intensity': 2.0,
            'duration_ms': payload.get('duration', 3000)
        })
        
        return {'success': True, 'beacon_pattern': pattern}
    
    async def _handle_toggle_mode(self, payload):
        """Toggle between display/control modes."""
        current_mode = payload.get('current_mode', 'display')
        new_mode = 'control' if current_mode == 'display' else 'display'
        
        return {'success': True, 'new_mode': new_mode}
    
    async def _handle_execute_command(self, payload):
        """Execute arbitrary visualization command."""
        cmd = payload.get('command')
        args = payload.get('args', {})
        
        if not cmd:
            raise ValueError("Missing required field: command")
        
        # Map common visualization commands
        if cmd == 'set_color':
            hue = float(args.get('hue', 0.55))  # Default cyan
            saturation = float(args.get('saturation', 0.8))
            lightness = float(args.get('lightness', 0.6))
            await self.state_manager.set_visual_param('color_hue', hue)
            await self.state_manager.set_visual_param('color_saturation', saturation)
            await self.state_manager.set_visual_param('color_lightness', lightness)
            return {'success': True, 'color': f'hsl({hue*360},{saturation*100}%,{lightness*100}%)'}
            
        elif cmd == 'rotate_form':
            angle = float(args.get('angle', 0))
            axis = args.get('axis', 'y')
            await self.state_manager.set_visual_param(f'rotation_{axis}', angle)
            return {'success': True, 'rotation': {axis: angle}}
            
        elif cmd == 'focus_perspective':
            fov = int(args.get('fov', 75))  # Field of view in degrees
            await self.state_manager.set_visual_param('field_of_view', fov)
            return {'success': True, 'fov': fov}
            
        else:
            raise ValueError(f"Unsupported visualization command: {cmd}")
    
    async def _handle_get_status(self, payload):
        """Get current system status."""
        state = await self.state_manager.get_current_state()
        
        return {
            'mode': self.mode,
            'port': self.port,
            'connected_clients': len(self.websockets),
            'current_phase': state.phase,
            'cycle': state.cycle,
            'confidence': state.confidence,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    async def _handle_set_visual_param(self, payload):
        """Set arbitrary visual parameter (for extensibility)."""
        param_name = payload.get('name')
        param_value = payload.get('value')
        
        if not param_name:
            raise ValueError("Missing required field: name")
        
        await self.state_manager.set_visual_param(param_name, param_value)
        return {'success': True, 'parameter': param_name, 'value': param_value}
    
    async def _send_response(self, writer, response):
        """Send JSON response to client."""
        try:
            data = json.dumps(response).encode() + b'\n'
            writer.write(data)
            await writer.drain()
        except Exception as e:
            print(f"❌ Error sending response: {e}")
    
    async def _log_trace(self, entry):
        """Append command trace to context_trace.jsonl."""
        trace_path = Path(__file__).parent.parent / 'state' / 'context_trace.jsonl'
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(trace_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')


async def main():
    parser = argparse.ArgumentParser(description='Holographic Projection Controller for C337')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket port (default: 8765)')
    parser.add_argument('--mode', choices=['SIM', 'HARDWARE'], default='SIM', 
                        help='Operating mode: SIM (HTML5 Canvas simulation) or HARDWARE (future pyserial/USB)')
    
    args = parser.parse_args()
    
    controller = HolographicProjectionController(port=args.port, mode=args.mode)
    
    try:
        await controller.start()
    except KeyboardInterrupt:
        print("\n🔮 Controller stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
