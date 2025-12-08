import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

try:
    from utils.emojis import star
except ImportError:
    star = "⭐"


class MemberCount(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.hybrid_command(name="membercount", aliases=["members"])
    async def membercount_cmd(self, ctx: commands.Context):
        """Show the current member count. Usage: .membercount or /membercount"""
        try:
            member_count = ctx.guild.member_count
            
            embed = discord.Embed(
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.utcnow(),
            )
            embed.set_author(
                name="Members",
                icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            )
            embed.description = f"{star} We currently have **{member_count}** members."
            
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error in membercount_cmd: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")


async def setup(client: commands.Bot):
    await client.add_cog(MemberCount(client))
