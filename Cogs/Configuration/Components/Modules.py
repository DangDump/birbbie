import discord
from utils.emojis import *
from utils.HelpEmbeds import NotYourPanel


async def ModuleOptions(Config, data=None):
    if not Config:
        Config = {"Modules": {}}
    return [
        discord.SelectOption(
            label="Infractions",
            description="",
            emoji = None,
            value="infractions",
            default=(
                Config.get("Modules", {}).get("infractions", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Promotions",
            description="",
            emoji = None,
            value="promotions",
            default=(
                Config.get("Modules", {}).get("promotions", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Message Quota",
            description="",
            value="Quota",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Quota", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Forums",
            description="",
            value="Forums",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Forums", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Daily Questions",
            emoji = None,
            description="",
            value="QOTD",
            default=(
                Config.get("Modules", {}).get("QOTD", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Leave Of Absence",
            description="",
            value="LOA",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("LOA", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Suspensions",
            description="",
            value="suspensions",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("suspensions", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Suggestions",
            description="",
            value="suggestions",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("suggestions", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Tickets",
            description="",
            value="Tickets",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Tickets", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Modmail",
            description="",
            value="Modmail",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Modmail", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Custom Commands",
            description="",
            value="customcommands",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("customcommands", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Staff List",
            description="",
            value="Staff List",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Staff List", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Staff Feedback",
            description="",
            value="Feedback",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Feedback", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Staff Panel",
            description="",
            value="Staff Database",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Staff Database", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Auto Response",
            value="Auto Responder",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("Auto Responder", False) or False
                if not data
                else False
            ),
        ),
        discord.SelectOption(
            label="Connection Roles",
            value="connectionroles",
            emoji = None,
            default=(
                Config.get("Modules", {}).get("connectionroles", False) or False
                if not data
                else False
            ),
        ),
    ]


class ModuleToggle(discord.ui.Select):
    def __init__(self, author, options: list):
        self.author = author
        super().__init__(
            placeholder="Modules",
            options=options,
            min_values=0,
            required=False,
        
            max_values=len(options),
        )

    async def callback(self, interaction: discord.Interaction):
        from Cogs.Configuration.Configuration import ConfigMenu
        from Cogs.Configuration.Configuration import Options

        Selected = self.values
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(embed=NotYourPanel(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {"_id": interaction.guild.id, "Modules": {}}
        elif "Modules" not in config:
            config["Modules"] = {}

        for module in config["Modules"]:
            config["Modules"][module] = False

        for module in Selected:
            config["Modules"][module] = True

        if "Modmail" in Selected and not interaction.guild.chunked:
            await interaction.guild.chunk()

        if "promotions" in Selected:
            from Cogs.Modules.promotions import SyncServer
            try:
                await SyncServer(interaction.client, interaction.guild)
            except:
                pass

        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}, upsert=True
        )
        Updated = await interaction.client.config.find_one({"_id": interaction.guild.id})

        view = discord.ui.View()
        view.add_item(ModuleToggle(interaction.user, await ModuleOptions(Updated)))
        view.add_item(ConfigMenu(Options(Updated), interaction.user))

        await interaction.edit_original_response(view=view)
        await interaction.followup.send(
            embed=discord.Embed(
                description="-# Select **Config Menu** and set up that module!",
                color=discord.Color.brand_green(),
            ).set_author(
                name="Modules Saved",
                icon_url="https://cdn.discordapp.com/emojis/1296530049381568522.webp?size=96&quality=lossless",
            ),
            ephemeral=True,
        )
