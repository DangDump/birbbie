import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

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
        premmies = os.getenv("PREMIUM_USERS", "").split(",")
        if ctx.author.id in premmies:
            HasPremium = True
        else:
            HasPremium = False

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
        # Load premium users from env and normalize to strings
        premmies = [p.strip() for p in os.getenv("PREMIUM_USERS", "").split(",") if p.strip()]
        author_id_str = str(getattr(ctx.author, "id", ""))

        if author_id_str not in premmies:
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

        # Try to send the message to the current channel as the bot
        try:
            await ctx.channel.send(message)
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