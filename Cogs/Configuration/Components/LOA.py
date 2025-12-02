import discord
from utils.emojis import *
from utils.HelpEmbeds import NotYourPanel


class LOAOptions(discord.ui.Select):
    def __init__(self, author: discord.Member):
        super().__init__(
            options=[
                discord.SelectOption(
                    label="LOA Channel", emoji = None
                ),
                discord.SelectOption(
                    label="LOA Audit Log",
                    emoji = None,
                    description="Logs for modify/force end.",
                ),
                discord.SelectOption(
                    label="LOA Role", emoji = None
                ),
            ]
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        from Cogs.Configuration.Configuration import Reset, ConfigMenu, Options

        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        await interaction.response.defer()
        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {
                "LOA": {},
                "Module Options": {},
                "_id": interaction.guild.id,
            }
        await Reset(
            interaction,
            lambda: LOAOptions(interaction.user),
            lambda: ConfigMenu(Options(Config), interaction.user),
        )
        Selection = self.values[0]
        view = discord.ui.View()
        if Selection == "LOA Role":
            view.add_item(
                LOARole(
                    self.author,
                    role=interaction.guild.get_role(
                        Config.get("LOA", {}).get("role"),
                    ),
                    message=interaction.message,
                )
            )

        if Selection == "LOA Channel":
            view.add_item(
                LOAChannel(
                    author=self.author,
                    channel=interaction.guild.get_channel(
                        Config.get("LOA", {}).get("channel"),
                    ),
                    message=interaction.message,
                )
            )

        if Selection == "LOA Audit Log":
            view.add_item(
                LogChannel(
                    author=self.author,
                    channel=interaction.guild.get_channel(
                        Config.get("LOA", {}).get("LogChannel"),
                    ),
                    message=interaction.message,
                )
            )

        await interaction.followup.send(view=view, ephemeral=True)


class LogChannel(discord.ui.ChannelSelect):
    def __init__(
        self,
        author: discord.Member,
        channel: discord.TextChannel = None,
        message: discord.Message = None,
    ):
        super().__init__(
            placeholder="Audit Log Channel",
            min_values=0,
            max_values=1,
            default_values=[channel] if channel else [],
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        )
        self.author = author
        self.channel = channel
        self.message = message

    async def callback(self, interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if config is None:
            config = {"_id": interaction.guild.id, "LOA": {}}
        elif "LOA" not in config:
            config["LOA"] = {}
        elif "LogChannel" not in config.get("Infraction", {}):
            config["LOA"]["LogChannel"] = None
        if self.values:
         config["LOA"]["LogChannel"] = self.values[0].id
        else:
            config["LOA"].pop("LogChannel", None)

        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )

        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await LOAEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


class LOAChannel(discord.ui.ChannelSelect):
    def __init__(
        self,
        author: discord.Member,
        channel: discord.TextChannel = None,
        message: discord.Message = None,
    ):
        super().__init__(
            min_values=0,
            max_values=1,
            default_values=[channel] if channel else [],
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        )
        self.author = author
        self.channel = channel
        self.message = message

    async def callback(self, interaction):
        from Cogs.Configuration.Configuration import ConfigMenu, Options

        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if config is None:
            config = {"_id": interaction.guild.id, "LOA": {}}
        elif "LOA" not in config:
            config["LOA"] = {}

        config["LOA"]["channel"] = self.values[0].id if self.values else None
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )

        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await LOAEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


class LOARole(discord.ui.RoleSelect):
    def __init__(
        self,
        author: discord.Member,
        role: discord.Role = None,
        message: discord.Message = None,
    ):
        super().__init__(
            min_values=0,
            max_values=1,
            default_values=[role] if role else [],
        )
        self.author = author
        self.role = role
        self.message = message

    async def callback(self, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if config is None:
            config = {"_id": interaction.guild.id, "LOA": {}}
        elif "LOA" not in config:
            config["LOA"] = {}

        config["LOA"]["role"] = self.values[0].id if self.values else None
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )
        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await LOAEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


async def LOAEmbed(
    interaction: discord.Interaction, config: dict, embed: discord.Embed
):
    config = await interaction.client.config.find_one({"_id": interaction.guild.id})
    if not config:
        config = {"LOA": {}}
    Channel = (
        interaction.guild.get_channel(config.get("LOA", {}).get("channel"))
        or "Not Configured"
    )
    LogChannel = (
        interaction.guild.get_channel(config.get("LOA", {}).get("LogChannel"))
        or "Not Configured"
    )

    Role = (
        interaction.guild.get_role(config.get("LOA", {}).get("role"))
        or "Not Configured"
    )
    if isinstance(Role, discord.Role):
        Role = Role.mention

    if isinstance(Channel, discord.TextChannel):
        Channel = Channel.mention
    if isinstance(LogChannel, discord.TextChannel):
        LogChannel = LogChannel.mention

    embed.set_author(name=f"{interaction.guild.name}", icon_url=interaction.guild.icon)
    embed.set_thumbnail(url=interaction.guild.icon)
    embed.description = "> This is where you can manage your server's LOA settings! LOA is a way for staff members to take a break from their duties. You can find out more at [the documentation](https://docs.astrobirb.dev/Modules/loa)."
    embed.add_field(
        name=" LOA",
        value=f"{replytop} `LOA Channel:` {Channel}\n{replymiddle} `LOA Audit Channel`: {LogChannel}\n{replybottom} `LOA Role:` {Role}\n\nIf you need help either go to the [support server](https://discord.gg/36xwMFWKeC) or read the [documentation](https://docs.astrobirb.dev/Modules/loa)",
        inline=False,
    )
    return embed
