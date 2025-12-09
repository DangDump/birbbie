import discord
from discord.ext import commands
from discord import app_commands
# List premium user IDs here (integers). Example: premmies = [123456789012345678]
premmies = [866515241256615988, 1394579020183638066, 1001926461344727150, 939826140024045569, 734413166615855184]

class Premium(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.hybrid_command(description="Run this command after purchasing premium.")
    async def premium(self, ctx: commands.Context):

        msg = await ctx.send(
            embed=discord.Embed(
                color=discord.Color.yellow(),
                description="Checking membership status...",
            ).set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
        )
        HasPremium = ctx.author.id in premmies

        if HasPremium:
            await msg.edit(
                embed=discord.Embed(
                    color=discord.Color.green(),
                    description="You have an active Premium membership. Your perks have been granted! Now, run `/config` in a server to activate your benefits.",
                ).set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
                )
            )
            await self.client.db["Subscriptions"].update_one(
                {"user": ctx.author.id},
                {
                    "$set": {
                        "user": ctx.author.id,
                        "guilds": [],
                        "created": discord.utils.utcnow(),
                        "Tokens": 1,
                    }
                },
                upsert=True,
            )
        else:
            await msg.edit(
                embed=discord.Embed(
                    color=discord.Color.orange(),
                    description="No, you're not one of the cool ones. To access premium, head to /Cogs/Modules/Utilities/premium.py for more information.",
                ).set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
                )
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Premium(client))
