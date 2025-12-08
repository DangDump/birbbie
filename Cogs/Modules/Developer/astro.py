import discord
from discord.ext import commands
import psutil
import os
from utils.emojis import *
from typing import Optional, Literal
from Cogs.Modules.Utilities.premium import premmies


def is_owner(user_id: int) -> bool:
    """Check if user ID matches the owner in env"""
    owner = os.getenv("OWNER")
    if not owner:
        return False
    owner_ids = [int(id) for id in owner.split(",")]
    return user_id in owner_ids


class management(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command()
    @commands.is_owner()
    async def account(self, ctx: commands.Context, user: discord.User):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.defer()

        Pre = await self.client.db["Subscriptions"].find_one({"user": user.id})
        B = await self.client.db["blacklists"].find_one({"user": user.id})

        PS = tick if Pre else no
        BS = tick if B else no

        view = ManageAccount(ctx.author, user)
        view.premium.style = (
            discord.ButtonStyle.green if Pre else discord.ButtonStyle.red
        )
        view.blacklisted.style = (
            discord.ButtonStyle.green if B else discord.ButtonStyle.red
        )

        embed = discord.Embed(
            title=f"@{user.display_name}",
            description=f"> **Premium:** {PS}\n> **Blacklisted:** {BS}",
            color=discord.Color.dark_embed(),
        )
        embed.set_thumbnail(url=user.avatar)
        embed.set_author(name=user.display_name, icon_url=user.avatar)
        await ctx.send(embed=embed, view=view)

    @commands.command()
    @commands.is_owner()
    async def version(self, ctx: commands.Context, v: str):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await self.client.db["Support Variables"].update_one(
            {"_id": 1}, {"$set": {"version": v}}, upsert=True
        )

    @commands.command()
    @commands.is_owner()
    async def vps(self, ctx: commands.Context):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.defer()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        embed = (
            discord.Embed(color=discord.Color.dark_embed())
            .add_field(
                name="`🧠` Memory",
                value=f"> `Total:` {memory.total / 1e9:.2f} GB\n> `Available:` {memory.available / 1e9:.2f} GB\n> `Usage:` {memory.percent}%",
                inline=False,
            )
            .add_field(
                name="` 💫 ` CPU Usage", value=f"{psutil.cpu_percent()}%", inline=False
            )
            .add_field(
                name="` 💿 ` Disk   ",
                value=f"> `Total:` {disk.total / 1e9:.2f} GB\n> `Used:` {disk.used / 1e9:.2f} GB\n> `Usage:` {disk.percent}%",
                inline=False,
            )
        )
        await ctx.author.send(embed=embed)

    @commands.hybrid_command(name="say", description="Make the bot say something (premium only).")
    async def say(self, ctx: commands.Context, *, message: str):
        """
        Send a message as the bot. Only users listed in the premmies list may use this.

        Behavior:
        - The bot will post `message` into the current channel formatted as **@author:** message.
        - If invoked as a slash command, the acknowledgement will be sent ephemerally to the user
          with the text: "{user} message was sent successfully." where {user} is replaced
          by the invoking user's display name.
        """
        # Check if user is premium
        if ctx.author.id not in premmies:
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

    @commands.group()
    @commands.is_owner()
    async def features(self, ctx: commands.Context):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return

    @features.command()
    @commands.is_owner()
    async def add(self, ctx: commands.Context, server: int, *, feature: str):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await self.client.db["Config"].update_one(
            {"_id": server}, {"$addToSet": {"Features": feature}}, upsert=True
        )
        await ctx.send(
            f"` ✅ ` **{ctx.author.display_name},** feature added to server `{server}`."
        )

    @features.command()
    @commands.is_owner()
    async def remove(self, ctx: commands.Context, server: int, *, features: str):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await self.client.db["Config"].update_one(
            {"_id": server}, {"$pull": {"Features": features}}, upsert=True
        )
        await ctx.send(
            f"` ❌ ` **{ctx.author.display_name},** feature removed from server `{server}`."
        )

    @commands.command()
    @commands.is_owner()
    async def analytics(self, ctx: commands.Context):
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        result = await self.client.db["analytics"].find({}).to_list(length=None)

        content = ""
        for x in result:
            for key, value in x.items():
                if key != "_id":
                    content += f"{key}: {value}\n"
            content += "\n"
            with open("analytics.txt", "w", encoding="utf-8") as file:
                file.write(content)

            await ctx.send(file=discord.File("analytics.txt"))

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        if not is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return

        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")
class ManageAccount(discord.ui.View):
    def __init__(self, author, user: discord.User):
        super().__init__()
        self.user = user
        self.author = author

    async def updateembed(
        self, user: discord.User, interaction: discord.Interaction = None
    ) -> discord.Embed:
        db = interaction.client.db
        premium_result = await db["Subscriptions"].find_one({"user": user.id})
        blacklist_result = await db["blacklists"].find_one({"user": user.id})

        premium_status = tick if premium_result else no
        blacklist_status = tick if blacklist_result else no

        embed = discord.Embed(
            title=f"@{user.display_name}",
            description=f"*> *Premium:** {premium_status}\n> **Blacklisted:** {blacklist_status}",
            color=discord.Color.dark_embed(),
        )
        embed.set_thumbnail(url=user.avatar)
        embed.set_author(name=user.display_name, icon_url=user.avatar)
        return embed

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.red)
    async def premium(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"**{interaction.user.display_name},** this is not your view!",
                    color=discord.Colour.dark_embed(),
                ),
                ephemeral=True,
            )

        premium_result = await interaction.client.db["Subscriptions"].find_one(
            {"user": self.user.id}
        )

        if premium_result:
            await interaction.client.db["Subscriptions"].delete_one(
                {"user": self.user.id}
            )
            PR = await interaction.client.db["Subscriptions"].find_one(
                {"user": self.user.id}
            )
            if PR:
                for server in PR.get("guilds", []):
                    Config = await self.client.db["Config"].find_one({"_id": server})
                    if Config is not None:
                        features = Config.get("Features", [])
                        if "PREMIUM" in features:
                            features.remove("PREMIUM")
                            await self.client.db["Config"].update_one(
                                {"_id": server}, {"$set": {"Features": features}}
                            )
                await interaction.client.db["Subscriptions"].delete_one(
                    {"user": self.user.id}
                )
            self.premium.style = discord.ButtonStyle.red
        else:
            await interaction.client.db["Subscriptions"].insert_one(
                {"user": self.user.id, "Tokens": 1, "guilds": []}
            )
            self.premium.style = discord.ButtonStyle.green

        embed = await self.updateembed(self.user, interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Blacklisted", style=discord.ButtonStyle.red)
    async def blacklisted(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"**{interaction.user.display_name},** this is not your view!",
                    color=discord.Colour.dark_embed(),
                ),
                ephemeral=True,
            )

        db = interaction.client.db
        blacklist_result = await db["blacklists"].find_one({"user": self.user.id})

        if blacklist_result:
            await db["blacklists"].delete_one({"user": self.user.id})
            self.blacklisted.style = discord.ButtonStyle.red
        else:
            await db["blacklists"].insert_one({"user": self.user.id})
            self.blacklisted.style = discord.ButtonStyle.green

        embed = await self.updateembed(self.user, interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"**{interaction.user.display_name},** this is not your view!",
                    color=discord.Colour.dark_embed(),
                ),
                ephemeral=True,
            )

        embed = await self.updateembed(self.user, interaction)
        await interaction.response.edit_message(embed=embed, view=self)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(management(client))
