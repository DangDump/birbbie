import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from utils.emojis import tick, star, wave

# Get emojis
try:
    from utils.emojis import tick, star, wave
except ImportError:
    tick = "✅"
    star = "⭐"
    wave = "👋"


class AFK(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.afk_users = {}  # {user_id: {"status": str, "timestamp": datetime, "mentions": [...]}}

    @commands.hybrid_command(name="afk", aliases=["away"])
    @app_commands.describe(status="Your AFK status (optional)")
    async def afk_cmd(self, ctx: commands.Context, *, status: str = None):
        """Set your AFK status. Usage: .afk {status} or /afk status: {status}"""
        try:
            # Validate status - no links, no role mentions, no @everyone/@here
            if status:
                # Check for links
                if "http://" in status or "https://" in status:
                    await ctx.send(f"❌ AFK status cannot contain links.")
                    return
                
                # Check for role mentions (@&)
                if "@&" in status or "<@&" in status:
                    await ctx.send(f"❌ AFK status cannot contain role mentions.")
                    return
                
                # Check for @everyone and @here
                if "@everyone" in status or "@here" in status:
                    await ctx.send(f"❌ AFK status cannot contain @everyone or @here.")
                    return
                
                # Limit length
                if len(status) > 100:
                    await ctx.send(f"❌ AFK status must be 100 characters or less.")
                    return
            
            # Set AFK status
            afk_status = status if status else "AFK"
            self.afk_users[ctx.author.id] = {
                "status": afk_status,
                "timestamp": datetime.utcnow(),
                "mentions": []
            }
            
            await ctx.send(f"{tick} {ctx.author.mention}, I've set your AFK status: {afk_status}")
        except Exception as e:
            print(f"Error in afk_cmd: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages and handle AFK mentions and returning from AFK"""
        if message.author.bot:
            return
        
        try:
            # Check if user is AFK and remove status if they send a message
            if message.author.id in self.afk_users:
                afk_data = self.afk_users[message.author.id]
                afk_time = datetime.utcnow() - afk_data["timestamp"]
                
                # Format time difference
                total_seconds = int(afk_time.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                
                # Count mentions
                mention_count = len(afk_data["mentions"])
                
                # Welcome back message
                welcome_msg = f"{wave} Welcome back {message.author.mention}! I removed your AFK. You were AFK for {time_str}."
                
                # Remove from AFK
                del self.afk_users[message.author.id]
                
                await message.reply(welcome_msg, mention_author=False)
                
                # Szend mentions embed in channel if they have any
                if mention_count > 0:
                    await self._send_mentions_embed(message, afk_data["mentions"])
            
            # Check if message mentions any AFK users
            await self._check_mentions(message)
        except Exception as e:
            print(f"Error in on_message: {e}")

    async def _check_mentions(self, message: discord.Message):
        """Check if message mentions any AFK users"""
        try:
            mentioned_users = message.mentions
            
            for mentioned_user in mentioned_users:
                if mentioned_user.id in self.afk_users:
                    afk_data = self.afk_users[mentioned_user.id]
                    time_ago = datetime.utcnow() - afk_data["timestamp"]
                    
                    # Format time difference
                    total_seconds = int(time_ago.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    
                    if hours > 0:
                        time_str = f"{hours}h {minutes}m ago"
                    else:
                        time_str = f"{minutes}m ago"
                    
                    # Send AFK notification
                    afk_msg = f"{star} {mentioned_user.display_name} is currently AFK: {afk_data['status']} ({time_str})"
                    await message.reply(afk_msg, mention_author=False)
                    
                    # Store mention
                    afk_data["mentions"].append({
                        "user": message.author,
                        "timestamp": datetime.utcnow(),
                        "message_link": message.jump_url
                    })
        except Exception as e:
            print(f"Error in _check_mentions: {e}")

    async def _send_mentions_embed(self, message: discord.Message, mentions: list):
        """Send paginated embed of mentions in channel"""
        try:
            user = message.author
            # Create pages (5 mentions per page)
            pages = []
            mentions_per_page = 5
            
            for i in range(0, len(mentions), mentions_per_page):
                page_mentions = mentions[i:i + mentions_per_page]
                
                embed = discord.Embed(
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(
                    name=f"You have {len(mentions)} mentions.",
                    icon_url=user.display_avatar.url
                )
                
                description = ""
                for mention_data in page_mentions:
                    mention_user = mention_data["user"]
                    mention_time = mention_data["timestamp"]
                    message_link = mention_data["message_link"]
                    
                    # Calculate time ago
                    time_ago = datetime.utcnow() - mention_time
                    total_seconds = int(time_ago.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    
                    if hours > 0:
                        time_str = f"{hours}h {minutes}m ago"
                    else:
                        time_str = f"{minutes}m ago"
                    
                    description += f"{mention_user.name} - {time_str}\n**Jump:** {message_link}\n\n"
                
                embed.description = description
                pages.append(embed)
            
            # Send first page in channel
            if pages:
                current_page = 0
                msg = await message.reply(embed=pages[current_page], mention_author=False)
                
                # Add pagination if multiple pages
                if len(pages) > 1:
                    await msg.add_reaction("⬅️")
                    await msg.add_reaction("➡️")
                    
                    def check(reaction, reacting_user):
                        return reacting_user == user and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == msg.id
                    
                    while True:
                        try:
                            reaction, reacting_user = await self.client.wait_for("reaction_add", check=check, timeout=300)
                            
                            if str(reaction.emoji) == "➡️":
                                current_page = min(current_page + 1, len(pages) - 1)
                            elif str(reaction.emoji) == "⬅️":
                                current_page = max(current_page - 1, 0)
                            
                            await msg.edit(embed=pages[current_page])
                            await msg.remove_reaction(reaction.emoji, reacting_user)
                        except asyncio.TimeoutError:
                            break
                        except Exception as e:
                            print(f"Error in pagination: {e}")
                            break
        except Exception as e:
            print(f"Error in _send_mentions_embed: {e}")


async def setup(client: commands.Bot):
    await client.add_cog(AFK(client))
