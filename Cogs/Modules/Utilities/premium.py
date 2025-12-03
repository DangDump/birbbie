import discord
from discord.ext import commands
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

    @commands.hybrid_command(name="say", description="Make the bot say something (premium only).")
    async def say(self, ctx: commands.Context, *, message: str):
        """
        Send a message as the bot. Only users listed in the PREMIUM_USERS env var may use this.

        Behavior:
        - The bot will post `message` into the current channel.
        - If invoked as a slash command, the acknowledgement will be sent ephemerally to the user
          with the text: "{user} message was sent successfully." where {user} is replaced
          by the invoking user's display name.
        """
        # Check membership against the module-level `premmies` list
        if ctx.author.id not in premmies:
            # Not premium — respond accordingly. If slash invoked, make it ephemeral.
            if getattr(ctx, "interaction", None):
                try:
                    await ctx.interaction.response.send_message(
                        "You must be a premium user to use this command.", ephemeral=True
                    )
                except Exception:
                    await ctx.send("You must be a premium user to use this command.")
            else:
                await ctx.send("You must be a premium user to use this command.")
            return

        # Format and send the message to the current channel as the bot
        formatted = f"**@{ctx.author.display_name}:** {message}"
        try:
            await ctx.channel.send(formatted)
        except Exception as e:
            # If sending failed, reply with an ephemeral error (if possible)
            if getattr(ctx, "interaction", None):
                try:
                    await ctx.interaction.response.send_message(
                        "Failed to send message. Ensure I have permission to send messages in this channel.",
                        ephemeral=True,
                    )
                except Exception:
                    await ctx.send("Failed to send message. Ensure I have permission to send messages in this channel.")
            else:
                await ctx.send("Failed to send message. Ensure I have permission to send messages in this channel.")
            return

        # Confirm to the user. If slash command, send ephemeral; otherwise, reply normally.
        confirm_text = f"{ctx.author.display_name} message was sent successfully."
        if getattr(ctx, "interaction", None):
            try:
                await ctx.interaction.response.send_message(confirm_text, ephemeral=True)
            except Exception:
                # If response already used, use followup
                try:
                    await ctx.interaction.followup.send(confirm_text, ephemeral=True)
                except Exception:
                    await ctx.send(confirm_text)
        else:
            await ctx.send(confirm_text)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Premium(client))
