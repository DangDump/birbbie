import discord
from discord.ext import commands
from utils.emojis import *

from utils.permissions import premium
from utils.HelpEmbeds import NoPremium, Support, NotYourPanel
from utils.ui import PMButton


async def Reset(i: discord.Interaction, *F):
    try:
        view = discord.ui.View()
        for E in F:
            view.add_item(E())
        await i.edit_original_response(view=view)
    except:
        pass


class ConfigMenu(discord.ui.Select):
    def __init__(self, options: list, author: discord.Member) -> None:
        self.author = author
        super().__init__(placeholder="Config Menu", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author.id:
            return await interaction.followup.send(embed=NotYourPanel(), ephemeral=True)

        from Cogs.Configuration.Components.Modules import ModuleToggle, ModuleOptions

        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {
                "_id": interaction.guild.id,
                "Modules": {},
                "Infractions": {},
                "Permissions": {},
            }
        view = discord.ui.View()

        selection = self.values[0]
        if interaction.user.id != self.author.id:
            return await interaction.followup.send(embed=embed, ephemeral=True)
        embed = discord.Embed(color=discord.Colour.dark_embed())

        await Reset(interaction, lambda: ConfigMenu(Options(Config), interaction.user))

        if selection == "Permissions":
            from Cogs.Configuration.Components.Permissions import (
                PermissionsEmbed,
                PermissionsUpdate,
            )
            from Cogs.Configuration.Components.AdvancedPermissions import (
                PermissionsDropdown,
            )

            embed = await PermissionsEmbed(interaction, Config, embed)
            view.add_item(
                PermissionsUpdate(
                    interaction.user,
                    "staffrole",
                    [
                        role
                        for role in interaction.guild.roles
                        if role.id in Config.get("Permissions", {}).get("staffrole", [])
                        or None
                    ],
                )
            )
            view.add_item(
                PermissionsUpdate(
                    interaction.user,
                    "adminrole",
                    [
                        role
                        for role in interaction.guild.roles
                        if role.id in Config.get("Permissions", {}).get("adminrole", [])
                        or None
                    ],
                )
            )
            view.add_item(PermissionsDropdown(interaction.user))
        elif selection == "Modules":
            embed.set_author(
                name=f"{interaction.guild.name}", icon_url=interaction.guild.icon
            )
            embed.set_thumbnail(url=interaction.guild.icon)
            embed.description = "> This is where you can toggle your server's modules! If you wanna know more about what these modules do head to the [documentation](https:/docs.astrobirb.dev)"

            view.add_item(
                ModuleToggle(
                    interaction.user,
                    await ModuleOptions(Config),
                )
            )
        elif selection == "infractions":
            from Cogs.Configuration.Components.Infractions import (
                InfractionEmbed,
                InfractionOption,
            )

            embed = await InfractionEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                InfractionOption(
                    interaction.user,
                )
            )
        elif selection == "promotions":
            from Cogs.Configuration.Components.Promotions import (
                PromotionEmbed,
                PSelect,
            )

            embed = await PromotionEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                PSelect(
                    interaction.user,
                    Config.get("Promo", {}).get("System", {}).get("type", "og"),
                )
            )
        elif selection == "Modmail":
            from Cogs.Configuration.Components.Modmail import (
                ModmailEmbed,
                ModmailOptions,
            )

            embed = await ModmailEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                ModmailOptions(
                    interaction.user,
                    Config.get("Module Options", {}).get("ModmailType", "channel"),
                )
            )
        elif selection == "Feedback":
            from Cogs.Configuration.Components.StaffFeedback import (
                StaffFeedbackEmbed,
                StaffFeedback,
            )

            embed = await StaffFeedbackEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                StaffFeedback(
                    interaction.user,
                )
            )
        elif selection == "Quota":
            from Cogs.Configuration.Components.MessageQuota import (
                MessageQuotaEmbed,
                QuotaOptions,
            )

            embed = await MessageQuotaEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                QuotaOptions(
                    interaction.user,
                )
            )
        elif selection == "Modcases Quota":
            from Cogs.Configuration.Components.MessageQuota import (
                ModcasesQuotaEmbed,
                ModcasesQuotaOptions,
            )

            embed = await ModcasesQuotaEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                ModcasesQuotaOptions(
                    interaction.user,
                )
            )
        elif selection == "LOA":
            from Cogs.Configuration.Components.LOA import (
                LOAEmbed,
                LOAOptions,
            )

            embed = await LOAEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                LOAOptions(
                    interaction.user,
                )
            )
        elif selection == "suggestions":
            from Cogs.Configuration.Components.Suggestions import (
                SuggestionsEmbed,
                Suggestions,
            )

            embed = await SuggestionsEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(
                Suggestions(
                    interaction.user,
                )
            )
        elif selection == "Staff Database":
            from Cogs.Configuration.Components.StaffPanel import (
                StaffPanelEmbed,
                StaffPanelOptions,
            )

            embed = await StaffPanelEmbed(interaction, embed)
            view = discord.ui.View()
            view.add_item(
                StaffPanelOptions(
                    interaction.user,
                )
            )
        elif selection == "customcommands":
            try:
                from Cogs.Configuration.Components.CustomCommands import (
                    CustomCommandsEmbed,
                    CustomCommands,
                )

                view = discord.ui.View()
                embed = await CustomCommandsEmbed(interaction, embed)
                view.add_item(
                    CustomCommands(
                        interaction.user,
                    )
                )
            except Exception as e:
                import traceback

                print(traceback.format_exc(e))
        elif selection == "Forums":
            from Cogs.Configuration.Components.Forums import ForumsOptions, ForumsEmbed

            embed = await ForumsEmbed(interaction, embed)

            view = discord.ui.View()
            view.add_item(ForumsOptions(interaction.user))
        elif selection == "suspensions":
            from Cogs.Configuration.Components.Suspensions import (
                SuspensionEmbed,
                SuspensionOptions,
            )

            embed = await SuspensionEmbed(interaction, Config, embed)
            view = discord.ui.View()
            view.add_item(SuspensionOptions(interaction.user))
        elif selection == "QOTD":
            from Cogs.Configuration.Components.QOTD import (
                QOTDEMbed,
                QOTDOptions,
            )

            daily = await interaction.client.db["qotd"].find_one(
                {"guild_id": interaction.guild.id}
            )

            if daily and daily.get("nextdate", None):
                options = [
                    discord.SelectOption(
                        label="Stop QOTD",
                        emoji = None,
                        description="End the daily questions.",
                    ),
                    discord.SelectOption(
                        label="Channel", emoji = None
                    ),
                    discord.SelectOption(
                        label="Webhook",
                        description="Send it as a webhook.",
                        emoji = None,
                    ),
                    discord.SelectOption(
                        label="Ping", emoji = None
                    ),
                    discord.SelectOption(
                        label="Preferences", emoji = None
                    ),
                ]
            else:
                options = [
                    discord.SelectOption(
                        label="Start QOTD",
                        emoji = None,
                        description="Start the daily questions. (Pressing this while its already started will restart it.)",
                    ),
                    discord.SelectOption(
                        label="Channel", emoji = None
                    ),
                    discord.SelectOption(
                        label="Webhook",
                        description="Send it as a webhook.",
                        emoji = None,
                    ),
                    discord.SelectOption(
                        label="Ping", emoji = None
                    ),
                    discord.SelectOption(
                        label="Preferences", emoji = None
                    ),
                ]

            embed = await QOTDEMbed(interaction, embed)
            view = discord.ui.View()
            view.add_item(QOTDOptions(interaction.user, options))
        elif selection == "Subscriptions":
            from Cogs.Configuration.Components.Subscriptions import (
                SubscriptionsEmbed,
                PremiumButtons,
            )

            result = await interaction.client.db["Subscriptions"].find_one(
                {"guilds": {"$in": [interaction.guild.id]}}
            )
            view = discord.ui.View()
            user = await interaction.client.db["Subscriptions"].find_one(
                {"user": interaction.user.id}
            )
            if not user and not result:
                view = PMButton()
            if user and not result:
                view = PremiumButtons(interaction.user)
                view.disable.disabled = True
            if user and result:
                view = PremiumButtons(interaction.user)
                view.disable.disabled = False
                view.enable.disabled = True
            embed = await SubscriptionsEmbed(interaction)
        elif selection == "Auto Responder":
            if not await premium(interaction.guild.id):
                return await interaction.followup.send(
                    embed=NoPremium(), view=Support()
                )

            from Cogs.Configuration.Components.AutoResponse import (
                AutoResponseEmbed,
                AutoResponderOptions,
            )

            embed = await AutoResponseEmbed(interaction, embed)
            view = discord.ui.View()
            view.add_item(
                AutoResponderOptions(
                    interaction.user,
                )
            )
        elif selection == "Integrations":
            from Cogs.Configuration.Components.integrations import (
                integrationsEmbed,
                Integrations,
            )

            view = discord.ui.View()
            view.add_item(Integrations(interaction.user))
            embed = await integrationsEmbed(interaction, embed=embed)
        elif selection == "Tickets":
            from Cogs.Configuration.Components.Tickets import TicketsEmbed, Tickets

            view = discord.ui.View()
            view.add_item(Tickets(interaction.user))
            embed = await TicketsEmbed(interaction, embed=embed)
        elif selection == "Staff List":
            from Cogs.Configuration.Components.stafflist import StaffListEmbed

            view = discord.ui.View()
            embed = await StaffListEmbed(interaction, embed=embed)
        view.add_item(ConfigMenu(Options(Config), interaction.user))
        await interaction.edit_original_response(embed=embed, view=view)


def DefaultEmbed(guild: discord.Guild):
    embed = discord.Embed(
        title="Configuration",
        description=" Select **an option** to manage your server's configuration.",
        color=discord.Color.dark_embed(),
    )
    embed.add_field(
        name=" Support Server",
        value="> If you ever have issues with the bot or require assistance come and talk to someone in [#get-support](https://discord.gg/23TD4vQXJA).",
        inline=False,
    )
    embed.add_field(
        name=" Documentation",
        value="> The best way to learn how to use **Astro Birb** is through the [**documentation**](https://astrobirb.dev)!",
        inline=False,
    )
    embed.set_thumbnail(url=guild.icon)
    embed.set_author(name=guild.name, icon_url=guild.icon)
    return embed


def Options(Config: dict = None):
    if not Config:
        Config = {"Modules": {}}
    Modules = Config.get("Modules", {})
    options = [
        discord.SelectOption(
            label="Permissions",
            description="Manage your server's permissions.",
            emoji = None,
        ),
        discord.SelectOption(
            label="Modules",
            description="Manage your server's modules",
            emoji = None,
        ),
        discord.SelectOption(
            label="Subscriptions",
            description="Manage your server's subscriptions",
            emoji = None,
        ),
        discord.SelectOption(
            label="Integrations",
            description="Use External APIs.",
            emoji = None,
        ),
    ]

    ModuleAddons = [
        discord.SelectOption(
            label="Infractions",
            description="",
            emoji = None,
            value="infractions",
        ),
        discord.SelectOption(
            label="Promotions",
            description="",
            emoji = None,
            value="promotions",
        ),
        discord.SelectOption(
            label="Message Quota",
            description="",
            value="Quota",
            emoji = None,
        ),
        discord.SelectOption(
            label="Modcases Quota",
            description="",
            value="Modcases Quota",
            emoji = None,
        ),
        discord.SelectOption(
            label="Leave Of Absence",
            description="",
            value="LOA",
            emoji = None,
        ),
        discord.SelectOption(
            label="Tickets",
            value="Tickets",
            emoji = None,
            description="",
        ),
        discord.SelectOption(
            label="Modmail",
            description="",
            value="Modmail",
            emoji = None,
        ),
        discord.SelectOption(
            label="Custom Commands",
            description="",
            value="customcommands",
            emoji = None,
        ),
        discord.SelectOption(
            label="Staff List",
            description="",
            value="Staff List",
            emoji = None,
        ),
        discord.SelectOption(
            label="Forums",
            description="",
            value="Forums",
            emoji = None,
        ),
        discord.SelectOption(
            label="Suspensions",
            description="",
            value="suspensions",
            emoji = None,
        ),
        discord.SelectOption(
            label="Daily Questions",
            emoji = None,
            description="",
            value="QOTD",
        ),
        discord.SelectOption(
            label="Suggestions",
            description="",
            value="suggestions",
            emoji = None,
        ),
        discord.SelectOption(
            label="Staff Feedback",
            description="",
            value="Feedback",
            emoji = None,
        ),
        discord.SelectOption(
            label="Staff Panel",
            description="",
            value="Staff Database",
            emoji = None,
        ),
        discord.SelectOption(
            label="Auto Response",
            value="Auto Responder",
            emoji = None,
        ),
    ]

    for module in ModuleAddons:
        if Modules.get(module.value, False):
            options.append(module)

    return options


class ConfigCog(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @commands.hybrid_command(description="Configure the bot for your servers needs")
    @commands.has_guild_permissions(manage_guild=True)
    async def config(self, ctx: commands.Context):
        Config = await self.client.config.find_one({"_id": ctx.guild.id})
        if (
            not Config
            or "Infraction" not in Config
            or not Config["Infraction"].get("types")
        ):
            if not Config:
                Config = {
                    "_id": ctx.guild.id,
                    "Modules": {},
                    "Infraction": {"types": []},
                }
            if not Config.get("Infraction"):
                Config["Infraction"] = {}
            Config["Infraction"]["types"] = [
                "Activity Notice",
                "Verbal Warning",
                "Warning",
                "Strike",
                "Demotion",
                "Termination",
            ]
            await self.client.config.update_one(
                {"_id": ctx.guild.id}, {"$set": Config}, upsert=True
            )

        options = Options(Config)
        view = discord.ui.View()
        view.add_item(ConfigMenu(options, ctx.author))

        embed = DefaultEmbed(ctx.guild)
        await ctx.send(embed=embed, view=view)

    @config.error
    async def PermsHandler(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"{no} **{ctx.author.display_name},** you are missing the `Manage Server` permission."
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConfigCog(client))
