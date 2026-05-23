#!/usr/bin/env python3
"""
Discord Reaction Feedback System - Presentational Knowledge Measurement

Posts suggestion messages with emoji reaction buttons for quick operator
"felt heard?" ratings. Implements P_096/P_097 right-hemisphere attunement
feedback channel without survey friction.

Usage:
    python discord_reaction_feedback.py post --message "SUGGESTION TEXT"
    python discord_reaction_feedback.py reactions --poll-interval 60
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

# Discord gateway client
try:
    from discord.ext import commands, tasks
    from discord import Interaction, Message, ButtonStyle
except ImportError:
    print("ERROR: discord.py not installed. Run: pip install discord.py")
    sys.exit(1)

# Configuration
DISCORD_TOKEN = os.getenv('LYLA_DISCORD_TOKEN')
if not DISCORD_TOKEN:
    # Try loading from shared location
    shared_path = Path('/droid/cl_shared/.env')
    if shared_path.exists():
        import dotenv
        dotenv.load_dotenv(shared_path)
        DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not DISCORD_TOKEN:
    print("ERROR: LYLA_DISCORD_TOKEN or DISCORD_BOT_TOKEN not set in environment")
    sys.exit(1)

FEEDBACK_EMOJIS = {
    'felt_heard': '✅',
    'off_target': '⚠️', 
    'helpful_incomplete': '💡',
    'not_relevant': '🔄'
}

LOG_PATH = Path(__file__).parent.parent / 'logs' / 'operator_fidelity.jsonl'


class ReactionFeedbackBot(commands.Bot):
    def __init__(self):
        intents = commands.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.feedback_count = 0
        
    async def setup_hook(self):
        print(f"Logged in as {self.user}")
        # Start background reaction aggregator if running in --poll mode
        if hasattr(self, '_in_poll_mode'):
            self.start_reaction_aggregator.start()
    
    async def on_ready(self):
        print(f'Reaction feedback system active. Tracking fidelity for operator engagement.')
    
    async def post_suggestion_with_feedback(self, message: str, channel_id: int):
        """Post a suggestion with emoji reactions for feedback."""
        try:
            channel = await self.fetch_channel(channel_id)
            
            # Create actions row with feedback buttons
            from discord.ui import View, Button
            
            view = View(timeout=86400)  # 24 hour timeout
            
            for key, emoji in FEEDBACK_EMOJIS.items():
                button = Button(
                    style=ButtonStyle.secondary,
                    emoji=emoji,
                    custom_id=f'feedback_{key}',
                    label=key.replace('_', ' ').title(),
                    disabled=False
                )
                view.add_item(button)
            
            msg = await channel.send(message, view=view)
            
            # Log the post event
            log_entry = {
                'event': 'suggestion_posted',
                'timestamp': datetime.utcnow().isoformat(),
                'message_preview': message[:100],
                'channel_id': channel_id,
                'message_id': msg.id
            }
            self._append_log(log_entry)
            
            print(f"Posted suggestion to channel {channel_id}, message ID: {msg.id}")
            return msg
        
        except Exception as e:
            print(f"ERROR posting suggestion: {e}")
            raise
    
    async def on_interaction(self, interaction: Interaction):
        """Handle reaction button clicks."""
        if not interaction.type.value == 'component':
            return
        
        if interaction.custom_id.startswith('feedback_'):
            feedback_type = interaction.custom_id.split('_')[1]
            
            log_entry = {
                'event': 'feedback_received',
                'timestamp': datetime.utcnow().isoformat(),
                'feedback_type': feedback_type,
                'user_id': interaction.user.id,
                'username': interaction.user.name,
                'message_id': interaction.message.id if interaction.message else None
            }
            self._append_log(log_entry)
            
            # Optional: Acknowledge the feedback privately
            await interaction.response.send_message(
                f"Thanks for your '{feedback_type}' feedback!",
                ephemeral=True
            )
    
    def _append_log(self, entry: dict):
        """Append JSONL log entry."""
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')


bot = ReactionFeedbackBot()


@bot.command()
async def post(ctx, channel_id: int, *, message: str):
    """Post a suggestion with feedback reactions to specified channel."""
    try:
        msg = await bot.post_suggestion_with_feedback(message, channel_id)
        await ctx.send(f"Suggestion posted (message ID: {msg.id})")
    except Exception as e:
        await ctx.send(f"Error posting: {e}")


@bot.event
async def on_raw_reaction_add(payload):
    """Handle emoji reactions on our messages."""
    if payload.emoji.name not in FEEDBACK_EMOJIS.values():
        return
    
    # Map reaction back to feedback type
    feedback_map = {v: k for k, v in FEEDBACK_EMOJIS.items()}
    feedback_type = feedback_map.get(payload.emoji.name)
    
    if not feedback_type:
        return
    
    log_entry = {
        'event': 'feedback_received',
        'timestamp': datetime.utcnow().isoformat(),
        'feedback_type': feedback_type,
        'user_id': payload.user_id,
        'message_id': payload.message_id,
        'channel_id': payload.channel_id
    }
    bot._append_log(log_entry)


def start_poll_mode(poll_interval: int = 60):
    """Start the bot in polling mode for background aggregation."""
    bot._in_poll_mode = True
    print(f"Starting reaction aggregator with {poll_interval}s poll interval...")
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Discord Reaction Feedback System')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # post command
    post_parser = subparsers.add_parser('post', help='Post suggestion with reactions')
    post_parser.add_argument('--channel-id', type=int, required=True, help='Target Discord channel ID')
    post_parser.add_argument('--message', '-m', required=True, help='Suggestion message to post')
    
    # poll command  
    poll_parser = subparsers.add_parser('poll', help='Poll reactions in background')
    poll_parser.add_argument('--interval', type=int, default=60, help='Polling interval in seconds')
    
    args = parser.parse_args()
    
    if args.command == 'post':
        asyncio.run(bot.post_suggestion_with_feedback(args.message, args.channel_id))
    elif args.command == 'poll':
        start_poll_mode(args.interval)
    else:
        parser.print_help()
