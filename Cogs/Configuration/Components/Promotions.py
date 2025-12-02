import discord
import traceback
from utils.emojis import *
import re
import typing
from utils.permissions import premium
from utils.HelpEmbeds import NoPremium, Support, NotYourPanel


class PSelect(discord.ui.Select):
    def __init__(
        self,
        author: discord.Member,
        system: typing.Literal["multi", "single", "og"] = "og",
    ):
        options = [
            discord.SelectOption(
                label="Promotion Channel",
                value="Promotion Channel",
                emoji = None,
                description="Set the channel for promotion messages.",
            ),
            discord.SelectOption(
                label="Promotions System",
                value="Promotions System",
                emoji = None,
                description="Choose which promotions system you want to use.",
            ),
            discord.SelectOption(
                label="Webhook",
                value="Webhook",
                emoji = None,
                description="Send promotion messages as a webhook.",
            ),
            discord.SelectOption(
                label="Cooldown",
                value="Cooldown",
                emoji = None,
                description="Set a cooldown for promoting users.",
            ),
            discord.SelectOption(
                label="Promotion Audit Log",
                value="Promotion Audit Log",
                emoji = None,
                description="Logs for creation, void, and modification.",
            ),
            discord.SelectOption(
                label="Customise Embed",
                value="Customise Embed",
                emoji = None,
            ),
            discord.SelectOption(
                label="Preferences",
                value="Preferences",
                emoji = None,
                description="Set preferences for promotion behaviour.",
            ),
        ]
        if system == "single":
            options.append(
                discord.SelectOption(
                    label="Hierarchy",
                    value="Single Hierarchy",
                    emoji = None,
                )
            )
        elif system == "multi":
            options.append(
                discord.SelectOption(
                    label="Hierarchy",
                    value="Multi Hierarchy",
                    emoji = None,
                )
            )

        super().__init__(options=options)
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        from Cogs.Configuration.Configuration import ConfigMenu, Options, Reset

        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )
        Selected = self.values[0]

        if Selected == "Cooldown":
            await interaction.response.send_modal(
                CoolDown(author=interaction.user, message=interaction.message)
            )
            return
        await interaction.response.defer()
        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {
                "Promo": {},
                "Module Options": {},
                "_id": interaction.guild.id,
            }
            
        await Reset(
            interaction,
            lambda: PSelect(interaction.user),
            lambda: ConfigMenu(Options(Config), interaction.user),
        )
        if Selected == "Promotion Channel":
            view = discord.ui.View()
            view.add_item(
                PromotionChannel(
                    interaction.user,
                    interaction.guild.get_channel(
                        Config.get("Promo", {}).get("channel")
                    ),
                    interaction.message,
                )
            )
            return await interaction.followup.send(
                view=view,
                ephemeral=True,
            )

        if Selected == "Webhook":
            if not await premium(interaction.guild.id):
                return await interaction.followup.send(
                    embed=NoPremium(), view=Support()
                )

            embed = await WebhookEmbed(interaction, Config)
            view = WebButton(interaction.user)
            view.add_item(WebhookToggle(interaction.user))
            return await interaction.followup.send(
                embed=embed, view=view, ephemeral=True
            )
        if Selected == "Promotion Audit Log":
            view = discord.ui.View()

            view.add_item(
                LogChannel(
                    interaction.user,
                    interaction.guild.get_channel(
                        Config.get("Promo", {}).get("LogChannel"),
                    ),
                    interaction.message,
                )
            )
            return await interaction.followup.send(
                view=view,
                ephemeral=True,
            )
        elif Selected == "Preferences":
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(
                name="Preferences",
                icon_url="https://cdn.discordapp.com/emojis/1160541147320553562.webp?size=96&quality=lossless",
            )
            embed.set_thumbnail(url=interaction.guild.icon)
            embed.description = "> **Promotion Issuer Button:** A disabled button that displays the username of the issuer at the bottom of the promotion embed.\n> **Auto Role:** Automatically roles the user the rank you specify on the promote command.\n> **Show Issuer:** If disabled on the embeds the issuer will not be displayed. It won't work with customised embeds & it will still appear on /promotions."
            if not Config.get("Module Options"):
                Config["Module Options"] = {}
            view = Preferences(interaction.user)
            view.children[0].label = (
                f"Auto Role ({'Enabled' if Config.get('Module Options', {}).get('autorole', True) else 'Disabled'})"
            )
            view.children[0].style = (
                discord.ButtonStyle.green
                if Config.get("Module Options", {}).get("autorole", True)
                else discord.ButtonStyle.red
            )
            view.children[1].style = (
                discord.ButtonStyle.green
                if Config.get("Module Options", {}).get("promotionissuer", False)
                else discord.ButtonStyle.red
            )

            view.children[1].label = (
                f"Issuer Button Display ({'Enabled' if Config.get('Module Options', {}).get('promotionissuer', False) else 'Disabled'})"
            )
            view.children[2].style = (
                discord.ButtonStyle.green
                if Config.get("Module Options", {}).get("pshowissuer", True)
                else discord.ButtonStyle.red
            )
            view.children[2].label = (
                f"Show Issuer ({'Enabled' if Config.get('Module Options', {}).get('pshowissuer', False) else 'Disabled'})"
            )
            return await interaction.followup.send(
                embed=embed, view=view, ephemeral=True
            )
        elif Selected == "Customise Embed":
            try:
                custom = await interaction.client.db["Customisation"].find_one(
                    {"guild_id": interaction.guild.id, "type": "Promotions"}
                )
                embed = None

                from Cogs.Configuration.Components.EmbedBuilder import (
                    DisplayEmbed,
                    Embed,
                )

                view = Embed(
                    interaction.user,
                    FinalFunction,
                    "Promotions",
                    {"thumb": "{staff.avatar}", "author_url": "{author.avatar}"},
                )
                if not custom:
                    embed = discord.Embed(color=discord.Color.dark_embed())
                    embed = discord.Embed(
                        title="Staff Promotion",
                        color=0x2B2D31,
                        description="* **User:** {staff.mention}\n* **Updated Rank:** {newrank}\n* **Reason:** {reason}",
                    )
                    embed.set_thumbnail(url=interaction.user.display_avatar)
                    embed.set_author(
                        name="Signed, {author.name}",
                        icon_url=interaction.user.display_avatar,
                    )
                    view.remove_item(view.Buttons)
                    view.remove_item(view.RemoveEmbed)
                    view.remove_item(view.Content)
                    view.remove_item(view.Permissions)
                    view.remove_item(view.ForumsChannel)
                    view.remove_item(view.Ping)
                    return await interaction.edit_original_response(
                        embed=embed, view=view
                    )

                embed = await DisplayEmbed(custom, interaction.user)
                view.remove_item(view.Buttons)
                view.remove_item(view.RemoveEmbed)
                view.remove_item(view.Content)
                view.remove_item(view.Permissions)
                view.remove_item(view.ForumsChannel)
                view.remove_item(view.Ping)
                view = Embed(
                    interaction.user,
                    FinalFunction,
                    "Promotions",
                    {
                        "thumb": (
                            interaction.user.display_avatar.url
                            if custom.get("embed", {}).get("thumbnail")
                            == "{author.avatar}"
                            else (
                                "{staff.avatar}"
                                if custom.get("embed", {}).get("thumbnail")
                                == "{staff.avatar}"
                                else custom.get("embed", {}).get("thumbnail")
                            )
                        ),
                        "author_url": (
                            interaction.user.display_avatar.url
                            if custom.get("embed", {}).get("author", {}).get("icon_url")
                            == "{author.avatar}"
                            else (
                                "{staff.avatar}"
                                if custom.get("embed", {})
                                .get("author", {})
                                .get("icon_url")
                                == "{staff.avatar}"
                                else custom.get("embed", {})
                                .get("author", {})
                                .get("icon_url")
                            )
                        ),
                        "image": (
                            interaction.user.display_avatar.url
                            if custom.get("embed", {}).get("image") == "{author.avatar}"
                            else (
                                "{staff.avatar}"
                                if custom.get("embed", {}).get("image")
                                == "{staff.avatar}"
                                else custom.get("embed", {}).get("image")
                            )
                        ),
                    },
                )
                return await interaction.edit_original_response(embed=embed, view=view)
            except Exception as e:
                traceback.print_exc(e)
        elif Selected == "Promotions System":
            config = await interaction.client.config.find_one(
                {"_id": interaction.guild.id}
            )
            system_type = config.get("Promo", {}).get("System", {}).get("type", "og")
            view = discord.ui.View()
            view.add_item(
                ModmailSystem(
                    interaction.user,
                    [
                        discord.SelectOption(
                            label="Single Hierarchy",
                            value="single",
                            default=(system_type == "single"),
                        ),
                        discord.SelectOption(
                            label="Multi Hierarchy",
                            value="multi",
                            default=(system_type == "multi"),
                        ),
                        discord.SelectOption(
                            label="OG System", value="og", default=(system_type == "og")
                        ),
                    ],
                    interaction.message,
                )
            )
            return await interaction.followup.send(
                view=view,
                ephemeral=True,
            )
        elif Selected == "Single Hierarchy":
            view = discord.ui.View()
            hierarchy_roles = (
                Config.get("Promo", {})
                .get("System", {})
                .get("single", {})
                .get("Hierarchy", [])
            )
            roles = [
                role for role in interaction.guild.roles if role.id in hierarchy_roles
            ]
            view.add_item(SingleHierarchy(interaction.user, roles))
            return await interaction.followup.send(
                view=view,
                ephemeral=True,
                content=" Select the roles for the hierarchy.\n\n No need to select them in order, they will be sorted automatically with discords role hierarchy system.",
            )
        elif Selected == "Multi Hierarchy":
            view = discord.ui.View()
            view.add_item(CreateAndDelete(interaction.user))

            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(
                name="Departments",
            )
            embed.set_thumbnail(url=interaction.guild.icon)
            embed.description = "Select **Create** to create a new department, **Delete** to delete a department, or **Modify** to modify a department."

            departments = (
                Config.get("Promo", {})
                .get("System", {})
                .get("multi", {})
                .get("Departments", [])
            )
            for department in departments:
                if (
                    isinstance(department, list)
                    and len(department) > 0
                    and isinstance(department[0], dict)
                ):
                    department = department[0]
                if isinstance(department, dict) and "ranks" in department:
                    roles = [
                        role.mention
                        for role_id in department["ranks"]
                        if (role := interaction.guild.get_role(role_id)) is not None
                    ]
                    RolesStr = "> " + ", ".join(roles) if roles else "No roles assigned"
                    if len(RolesStr) > 1024:
                        RolesStr = RolesStr[:1021] + "..."
                    embed.add_field(name=department.get("name"), value=RolesStr)
                    if len(embed.fields) >= 25:
                        break

            return await interaction.followup.send(
                view=view,
                ephemeral=True,
                embed=embed,
            )
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": Config}
        )
        await interaction.response.edit_message(view=self, content=None)


async def FinalFunction(interaction: discord.Interaction, d=None):
    from Cogs.Configuration.Configuration import ConfigMenu, Options

    embed = interaction.message.embeds[0]
    if embed:
        data = {
            "content": interaction.message.content,
            "creator": interaction.user.id,
            "embed": {
                "title": embed.title,
                "description": embed.description,
                "thumbnail": d.get("thumb"),
                "image": d.get("image"),
                "color": f"{embed.color.value:06x}" if embed.color else None,
                "author": {
                    "name": embed.author.name if embed.author else None,
                    "icon_url": d.get("author_url"),
                },
                "fields": [
                    {
                        "name": field.name,
                        "value": field.value,
                        "inline": field.inline,
                    }
                    for field in embed.fields
                ],
            },
        }

    await interaction.client.db["Customisation"].update_one(
        {"guild_id": interaction.guild.id, "type": "Promotions"},
        {"$set": data},
        upsert=True,
    )
    Config = await interaction.client.config.find_one({"_id": interaction.guild.id})

    view = discord.ui.View()
    view.add_item(
        PSelect(
            interaction.user,
            Config.get("Promo", {}).get("System", {}).get("type", "og"),
        )
    )
    view.add_item(ConfigMenu(Options(Config=Config), interaction.user))
    await interaction.response.edit_message(
        embed=await PromotionEmbed(
            interaction, Config, discord.Embed(color=discord.Color.dark_embed())
        ),
        view=view,
    )


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
            config = {"_id": interaction.guild.id, "Promo": {}}
        elif "Promo" not in config:
            config["Promo"] = {}
        elif "LogChannel" not in config.get("Promo", {}):
            config["Promo"]["LogChannel"] = None

        config["Promo"]["LogChannel"] = self.values[0].id if self.values else None
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )

        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await PromotionEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


class CoolDown(discord.ui.Modal):
    def __init__(self, author: discord.Member, message: discord.Message):
        super().__init__(title="Promotion Cooldown")
        self.author = author
        self.message = message
        self.Days = discord.ui.TextInput(
            label="How many days is this cooldown?",
            placeholder="Eg. 2. Type 0 if you don't want a cooldown.",
            required=False,
        )

        self.add_item(self.Days)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )
        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if config is None:
            config = {"_id": interaction.guild.id, "Promo": {}}
        elif "Promo" not in config:
            config["Promo"] = {}
        elif "Cooldown" not in config.get("Promo", {}):
            config["Promo"]["Cooldown"] = None
        config["Promo"]["Cooldown"] = self.Days.value if self.Days else None
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )

        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await PromotionEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


class Preferences(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__()
        self.author = author

    async def ToggleOption(
        self, interaction: discord.Interaction, button: discord.ui.Button, Option: str
    ):
        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {
                "Infraction": {},
                "Module Options": {},
                "_id": interaction.guild.id,
            }
        if not Config.get("Module Options"):
            Config["Module Options"] = {}

        if Config.get("Module Options", {}).get(Option, False):
            Config["Module Options"][Option] = False
            button.style = discord.ButtonStyle.red
            if Option == "promotionissuer":
                button.label = f"Issuer Button Display ({'Enabled' if Config.get('Module Options', {}).get('promotionissuer', False) else 'Disabled'})"
            elif Option == "pshowissuer":
                button.label = f"Show Issuer ({'Enabled' if Config.get('Module Options', {}).get('pshowissuer', True) else 'Disabled'})"
            elif Option == "autorole":
                button.label = f"Auto Role ({'Enabled' if Config.get('Module Options', {}).get('autorole', True) else 'Disabled'})"
        else:
            Config["Module Options"][Option] = True
            button.style = discord.ButtonStyle.green
            if Option == "promotionissuer":
                button.label = f"Issuer Button Display ({'Enabled' if Config.get('Module Options', {}).get('promotionissuer', False) else 'Disabled'})"
            elif Option == "pshowissuer":
                button.label = f"Show Issuer ({'Enabled' if Config.get('Module Options', {}).get('pshowissuer', True) else 'Disabled'})"
            elif Option == "autorole":
                button.label = f"Auto Role ({'Enabled' if Config.get('Module Options', {}).get('autorole', True) else 'Disabled'})"

        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": Config}
        )
        await interaction.response.edit_message(content=None, view=self)

    @discord.ui.button(label="Auto Role (Enabled)", style=discord.ButtonStyle.green)
    async def AutoRole(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.ToggleOption(interaction, button, "autorole")

    @discord.ui.button(
        label="Issuer Button Display (Disabled)", style=discord.ButtonStyle.red
    )
    async def IssuerButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.ToggleOption(interaction, button, "promotionissuer")

    @discord.ui.button(label="Show Issuer (Disable)", style=discord.ButtonStyle.green)
    async def ShowIssuer(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.ToggleOption(interaction, button, "pshowissuer")


class CreateAndDelete(discord.ui.Select):
    def __init__(self, author: discord.Member):
        super().__init__(
            placeholder="Manage Departments",
            options=[
                discord.SelectOption(
                    label="Create", value="create", emoji = None
                ),
                discord.SelectOption(
                    label="Delete",
                    value="delete",
                    emoji = None,
                ),
                discord.SelectOption(
                    label="Modify", value="modify", emoji = None
                ),
            ],
            min_values=1,
            max_values=1,
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        if self.values[0] == "create":
            return await interaction.response.send_modal(
                CreateDeleteDepartment(interaction.user, "create")
            )
        elif self.values[0] == "modify":
            await interaction.response.defer()

            config = await interaction.client.config.find_one(
                {"_id": interaction.guild.id}
            )
            if not config:
                config = {
                    "_id": interaction.guild.id,
                    "Promo": {"System": {"multi": {"Departments": []}}},
                }
            if "multi" not in config["Promo"]["System"]:
                config["Promo"]["System"]["multi"] = {"Departments": []}

            IsEmpty = (
                not config.get("Promo", {})
                .get("System", {})
                .get("multi", {})
                .get("Departments", [])
            )
            if IsEmpty:
                return await interaction.followup.send(
                    content=f"{no} **{interaction.user.display_name}**, there are no departments to modify.",
                    ephemeral=True,
                )
            view = discord.ui.View()
            view.add_item(
                ModifyDepartment(
                    interaction.user,
                    [
                        department["name"]
                        for departments_group in config["Promo"]["System"]["multi"][
                            "Departments"
                        ]
                        for department in departments_group
                    ],
                )
            )
            await interaction.edit_original_response(
                content=f"{tick} **{interaction.user.display_name}**, select the department to modify.",
                view=view,
                embed=None,
            )
            return
        
        elif self.values[0] == "delete":
            return await interaction.response.send_modal(
                CreateDeleteDepartment(interaction.user, "delete")
            )



class SingleHierarchy(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, roles: list[discord.Role]):
        super().__init__(
            placeholder="Select staff roles",
            min_values=1,
            max_values=25,
            default_values=roles,
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        Selected = [RoleID.id for RoleID in self.values]
        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {
                "_id": interaction.guild.id,
                "Promo": {"System": {"single": {"Hierarchy": []}}},
            }

        if "single" not in config["Promo"]["System"]:
            config["Promo"]["System"]["single"] = {"Hierarchy": []}

        config["Promo"]["System"]["single"]["Hierarchy"] = Selected
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )

        await interaction.response.edit_message(
            view=None,
            content=f"{tick} **{interaction.user.display_name}**, the hierarchy has been updated!",
            embed=None,
        )


class ModmailSystem(discord.ui.Select):
    def __init__(self, author: discord.Member, options: list, msg: discord.Message):
        super().__init__(
            placeholder="Promotions System",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.author = author
        self.msg = msg

    async def callback(self, interaction: discord.Interaction):
        from Cogs.Configuration.Configuration import ConfigMenu, Options
        from Cogs.Modules.promotions import SyncServer

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {
                "_id": interaction.guild.id,
                "Promo": {"System": {"type": "og"}},
            }

        if "Promo" not in config:
            config["Promo"] = {"System": {"type": "og"}}
        if "System" not in config["Promo"]:
            config["Promo"]["System"] = {"type": "og"}
        if self.values:
            config["Promo"]["System"]["type"] = self.values[0]
        else:
            return await interaction.response.send_message(
                content=f"{crisis} **{interaction.user.display_name}**, no system type selected.",
                ephemeral=True,
            )
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )

        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name}**, the promotions system has been updated to {self.values[0]}!",
            view=None,
        )
        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})

        view = discord.ui.View()
        view.add_item(
            PSelect(
                interaction.user,
                Config.get("Promo", {}).get("System", {}).get("type", "og"),
            )
        )
        view.add_item(ConfigMenu(Options(Config=Config), interaction.user))
        await SyncServer(interaction.client, interaction.guild)
        try:
            await self.msg.edit(
                embed=await PromotionEmbed(
                    interaction, Config, discord.Embed(color=discord.Color.dark_embed())
                ),
                view=view,
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                content=f"{crisis} **{interaction.user.display_name}**, I couldn't update the message. You will need to reload the page to see the new options.",
            )


class ModifyDepartment(discord.ui.Select):
    def __init__(self, author: discord.Member, departments: list):
        options = [
            discord.SelectOption(label=department, value=department)
            for department in departments
        ]
        super().__init__(
            placeholder="Select a department to modify",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )
        selected_department = self.values[0]

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {
                "_id": interaction.guild.id,
                "Promo": {"System": {"multi": {"Departments": []}}},
            }
        if "multi" not in config["Promo"]["System"]:
            config["Promo"]["System"]["multi"] = {"Departments": []}

        department = next(
            (
                d
                for group in config["Promo"]["System"]["multi"]["Departments"]
                for d in group
                if d["name"] == selected_department
            ),
            None,
        )

        if not department:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** department not found!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        roles = [
            interaction.guild.get_role(role_id)
            for role_id in department.get("ranks", [])
            if interaction.guild.get_role(role_id) is not None
        ]

        view = discord.ui.View()
        view.add_item(MultiHierarchy(interaction.user, selected_department, roles))
        await interaction.response.edit_message(
            content=f" Select the roles for the department `{selected_department}`.\n\n No need to select them in order, they will be sorted automatically with discords role hierarchy system.",
            embed=None,
            view=view,
        )


class MultiHierarchy(discord.ui.RoleSelect):
    def __init__(
        self, author: discord.Member, department: str, roles: list[discord.Role]
    ):
        super().__init__(
            placeholder="Select department roles",
            min_values=1,
            max_values=25,
            default_values=roles,
        )
        self.author = author
        self.department = department

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        Selected = [role.id for role in self.values]
        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {
                "_id": interaction.guild.id,
                "Promo": {"System": {"multi": {"Departments": []}}},
            }
        if "multi" not in config["Promo"]["System"]:
            config["Promo"]["System"]["multi"] = {
                "Departments": [{"name": self.department, "ranks": []}]
            }

        for departments_group in config["Promo"]["System"]["multi"]["Departments"]:
            for department in departments_group:
                if department["name"] == self.department:
                    department["ranks"] = Selected
                    break

        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        await interaction.response.edit_message(
            view=None,
            content=f"{tick} **{interaction.user.display_name}**, the hierarchy for the department `{self.department}` has been updated!",
            embed=None,
        )


class CreateDeleteDepartment(discord.ui.Modal):
    def __init__(self, author: discord.Member, action: str):
        super().__init__(title="Create/Delete Department", timeout=None)
        self.author = author
        self.action = action

        self.name = discord.ui.TextInput(
            label="Department Name",
            placeholder="Enter the department name",
            required=True,
        )
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not config:
            config = {
                "_id": interaction.guild.id,
                "Promo": {"System": {"multi": {"Departments": []}}},
            }

        if "multi" not in config["Promo"]["System"]:
            config["Promo"]["System"]["multi"] = {"Departments": []}

        DepartmentName = self.name.value
        if self.action == "create":
            if any(
                department["name"] == DepartmentName
                for departments_group in config["Promo"]["System"]["multi"][
                    "Departments"
                ]
                for department in departments_group
            ):
                return await interaction.response.send_message(
                    f"{no} **{interaction.user.display_name},** I couldn't find the department.",
                    ephemeral=True,
                )

            config["Promo"]["System"]["multi"]["Departments"].append(
                [{"name": DepartmentName, "ranks": []}]
            )

            await interaction.client.config.update_one(
                {"_id": interaction.guild.id}, {"$set": config}
            )

            view = discord.ui.View()
            view.add_item(MultiHierarchy(interaction.user, DepartmentName, []))
            await interaction.response.edit_message(
                content=" Select the roles for this department's hierarchy.\n\n No need to select them in order, they will be sorted automatically with discords role hierarchy system.",
                view=view,
            )
            return

        elif self.action == "delete":
            config["Promo"]["System"]["multi"]["Departments"] = [
                [
                    department
                    for department in departments_group
                    if department["name"] != DepartmentName
                ]
                for departments_group in config["Promo"]["System"]["multi"][
                    "Departments"
                ]
            ]

            await interaction.client.config.update_one(
                {"_id": interaction.guild.id}, {"$set": config}
            )

            await interaction.response.edit_message(
                content=f"{tick} **{interaction.user.display_name}**, the department `{DepartmentName}` has been deleted!",
                view=None,
            )


class PromotionChannel(discord.ui.ChannelSelect):
    def __init__(
        self,
        author: discord.Member,
        channel: discord.TextChannel = None,
        message: discord.Message = None,
    ):
        super().__init__(
            placeholder="Promotion Channel",
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
            config = {"_id": interaction.guild.id, "Promo": {}}
        elif "Promo" not in config:
            config["Promo"] = {}

        config["Promo"]["channel"] = self.values[0].id if self.values else None
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": config}
        )
        Updated = await interaction.client.config.find_one(
            {"_id": interaction.guild.id}
        )

        await interaction.response.edit_message(content=None)
        try:
            await self.message.edit(
                embed=await PromotionEmbed(
                    interaction,
                    Updated,
                    discord.Embed(color=discord.Color.dark_embed()),
                ),
            )
        except:
            pass


class WebhookDesign(discord.ui.Modal):
    def __init__(self, author: discord.Member):
        super().__init__(title="Webhook Design")
        self.author = author
        self.username = discord.ui.TextInput(
            label="Username", placeholder="The username of the webhook"
        )
        self.AvatarURL = discord.ui.TextInput(
            label="Avatar Link",
            placeholder="A avatar link, I recommend using something like Imgur.",
        )
        self.add_item(self.username)
        self.add_item(self.AvatarURL)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )
        if not await premium(interaction.guild.id):
            return await interaction.response.send_message(
                embed=NoPremium(), view=Support()
            )
        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if Config is None:
            Config = {"_id": interaction.guild.id, "Promo": {"Webhook": {}}}
        if "Promo" not in Config:
            Config["Promo"] = {}
        if "Webhook" not in Config["Promo"]:
            Config["Promo"]["Webhook"] = {}
        if not self.AvatarURL.value.strip():
            self.AvatarURL.value = interaction.client.user.display_avatar.url
        AV = self.AvatarURL.value.strip()
        pattern = r"^https?://.*\.(png|jpg|jpeg|gif|webp)(\?.*)?$"
        if not re.match(pattern, AV, re.IGNORECASE):
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** the avatar link provided is not a valid image URL!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        Config["Promo"]["Webhook"] = {
            "Username": self.username.value,
            "Avatar": self.AvatarURL.value,
        }
        await interaction.client.config.update_one(
            {"_id": interaction.guild.id}, {"$set": Config}
        )
        await interaction.response.edit_message(
            embed=await WebhookEmbed(interaction, Config)
        )


class WebhookToggle(discord.ui.Select):
    def __init__(self, author: discord.Member):
        options = [
            discord.SelectOption(
                label="Enable",
                value="enable",
            ),
            discord.SelectOption(label="Disable", value="disable"),
        ]
        super().__init__(
            placeholder="Select", min_values=1, max_values=1, options=options
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:

            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {"Promo": {}, "_id": interaction.guild.id}
        if "Promo" not in Config:
            Config["Promo"] = {}
        if "Webhook" not in Config["Promo"]:
            Config["Promo"]["Webhook"] = {}
        if "Enabled" not in Config["Promo"]["Webhook"]:
            Config["Promo"]["Webhook"]["Enabled"] = False

        selection = self.values[0]
        if selection == "enable":

            Config["Promo"]["Webhook"]["Enabled"] = True
            await interaction.client.config.update_one(
                {"_id": interaction.guild.id}, {"$set": Config}
            )
            await interaction.response.edit_message(
                embed=await WebhookEmbed(interaction, Config)
            )

        elif selection == "disable":
            Config["Promo"]["Webhook"]["Enabled"] = False
            await interaction.client.config.update_one(
                {"_id": interaction.guild.id}, {"$set": Config}
            )

            await interaction.response.edit_message(
                embed=await WebhookEmbed(interaction, Config)
            )


class WebButton(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.author = author

    @discord.ui.button(
        label="Customise Webhook", style=discord.ButtonStyle.blurple, row=3
    )
    async def B(self, I: discord.Interaction, B: discord.ui.Button):
        await I.response.send_modal(WebhookDesign(self.author))


async def WebhookEmbed(interaction: discord.Interaction, Config: dict):
    Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
    if not Config:
        Config = {"Promo": {}, "_id": interaction.guild.id}

    embed = discord.Embed()
    embed.set_author(
        name="Webhook",
        icon_url="https://cdn.discordapp.com/emojis/1400197752339824821.webp?size=96",
    )
    WebhookSettings = Config.get("Promo", {}).get("Webhook", {})
    enabled = WebhookSettings.get("Enabled", False)
    username = WebhookSettings.get("Username", None) or "Not Set"
    avatar = WebhookSettings.get("Avatar", None) or "Not Set"
    embed.add_field(
        name=" Webhook Settings",
        value=f"> {replytop} **Enabled:** {'True' if enabled else 'False'}\n> {replymiddle} **Username:** {username}\n> {replybottom} **Avatar:** {avatar}",
    )
    return embed


async def PromotionEmbed(
    interaction: discord.Interaction, Config: dict, embed: discord.Embed
):
    Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
    if not Config:
        Config = {"Promo": {}, "_id": interaction.guild.id}
    Channel = (
        interaction.guild.get_channel(Config.get("Promo", {}).get("channel"))
        or "Not Configured"
    )
    Promo = Config.get("Promo", {})
    Cooldown = Promo.get("Cooldown")
    Days = f"{Cooldown} Days" if Cooldown is not None else "Not Set"
    System = Promo.get("System", {}).get("type", "Default")
    if isinstance(Channel, discord.TextChannel):
        Channel = Channel.mention

    embed.set_author(name=f"{interaction.guild.name}", icon_url=interaction.guild.icon)
    embed.set_thumbnail(url=interaction.guild.icon)
    embed.description = "> This is where you can manage your server's promotion settings! Promotions are a way to give staff members more power. You can find out more at [the documentation](https://docs.astrobirb.dev/Modules/promotions)."
    embed.add_field(
        name=" Promotions",
        value=f"> {replytop} `System:` {System}\n> {replymiddle} `Promotion Channel:` {Channel}\n> {replybottom} `Cooldown:` {Days}\n\nIf you need help either go to the [support server](https://discord.gg/36xwMFWKeC) or read the [documentation](https://docs.astrobirb.dev/Modules/promotions).",
        inline=False,
    )
    return embed
