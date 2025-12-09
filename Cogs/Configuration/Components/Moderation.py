import discord
from utils.emojis import *
from utils.HelpEmbeds import NotYourPanel, BotNotConfigured


class ModerationOption(discord.ui.Select):
    def __init__(self, author: discord.Member):
        super().__init__(
            options=[
                discord.SelectOption(
                    label="Role & Channel Configuration",
                    description="Configure roles and channels for moderation",
                    emoji="⚙️"
                ),
                discord.SelectOption(
                    label="View Commands",
                    description="View all available moderation commands",
                    emoji="📋"
                ),
            ]
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        from Cogs.Configuration.Configuration import Reset, ConfigMenu, Options

        await interaction.response.defer()
        if interaction.user.id != self.author.id:
            return await interaction.followup.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            Config = {
                "Modules": {},
                "moderation": {},
                "_id": interaction.guild.id,
            }
        
        await Reset(
            interaction,
            lambda: ModerationOption(interaction.user),
            lambda: ConfigMenu(Options(Config), interaction.user),
        )

        view = discord.ui.View()
        selection = self.values[0]
        embed = discord.Embed(color=discord.Colour.dark_embed())

        if selection == "Role & Channel Configuration":
            embed.title = "Moderation Configuration"
            embed.description = (
                "Configure the following role and channel IDs for the moderation system:\n\n"
                "**Warn, Mute & Ban Request** - Role that can warn, mute, and request bans\n"
                "**Kick & Ban** - Role that can kick and ban users\n"
                "**Punishment Whitelist (Staff Role)** - Role that is exempt from punishments\n"
                "**Log Channel** - Channel for punishment logs\n"
                "**Ban Request Channel** - Channel for ban requests\n"
                "**Action Proofs Channel** - Channel for proof attachments\n\n"
                "Click the button below to configure these settings."
            )
            
            view.add_item(ConfigureModerationButton(interaction.user))

        elif selection == "View Commands":
            embed = await get_moderation_commands_embed()
            view.add_item(ModerationOption(interaction.user))

        await interaction.followup.send(embed=embed, view=view)


class ConfigureModerationButton(discord.ui.Button):
    def __init__(self, author: discord.Member):
        super().__init__(label="Configure", style=discord.ButtonStyle.green)
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        
        # Load current config
        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        mod_config = config.get("moderation", {}) if config else {}
        
        # First view: Role selectors (3 items)
        role_view = discord.ui.View()
        role_view.add_item(RoleSelector(interaction.user, "Warn, Mute & Ban Request", "warn_mute_role", mod_config))
        role_view.add_item(RoleSelector(interaction.user, "Kick & Ban", "kick_ban_role", mod_config))
        role_view.add_item(RoleSelector(interaction.user, "Punishment Whitelist (Staff Role)", "whitelist_role", mod_config))
        
        role_embed = discord.Embed(
            title="Configure Moderation Roles",
            description="Select the roles for moderation permissions:",
            color=discord.Colour.dark_embed()
        )
        
        await interaction.followup.send(embed=role_embed, view=role_view, ephemeral=True)
        
        # Second view: Channel selectors (3 items)
        channel_view = discord.ui.View()
        channel_view.add_item(ChannelSelector(interaction.user, "Log Channel", "log_channel", mod_config))
        channel_view.add_item(ChannelSelector(interaction.user, "Ban Request Channel", "ban_request_channel", mod_config))
        channel_view.add_item(ChannelSelector(interaction.user, "Action Proofs Channel", "action_proofs_channel", mod_config))
        
        channel_embed = discord.Embed(
            title="Configure Moderation Channels",
            description="Select the channels for moderation logging and requests:",
            color=discord.Colour.dark_embed()
        )
        
        await interaction.followup.send(embed=channel_embed, view=channel_view, ephemeral=True)


class RoleSelector(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, label: str, config_key: str, current_config: dict):
        super().__init__(
            placeholder=f"Select {label}",
            min_values=1,
            max_values=1
        )
        self.author = author
        self.label_text = label
        self.config_key = config_key
        self.current_config = current_config

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        
        selected_role = self.values[0]
        
        # Map config_key to database field name
        key_mapping = {
            "warn_mute_role": "WARN_MUTE_BANREQUEST_ROLE",
            "kick_ban_role": "KICK_BAN_ROLE",
            "whitelist_role": "PUNISHMENT_WHITELIST_ROLE",
            "log_channel": "LOG_CHANNEL_ID",
            "ban_request_channel": "BAN_REQUEST_CHANNEL_ID",
            "action_proofs_channel": "ACTION_PROOFS_CHANNEL_ID",
        }
        
        db_key = key_mapping.get(self.config_key, self.config_key)
        
        try:
            await interaction.client.config.update_one(
                {"_id": interaction.guild.id},
                {
                    "$set": {
                        f"moderation.{db_key}": selected_role.id
                    }
                },
                upsert=True,
            )
            await interaction.followup.send(
                f"{tick} {self.label_text} set to {selected_role.mention}",
                ephemeral=True,
            )
        except Exception as e:
            print(f"Error saving role config: {e}")
            await interaction.followup.send(
                f"{no} Error saving configuration: {str(e)}",
                ephemeral=True,
            )


class ChannelSelector(discord.ui.ChannelSelect):
    def __init__(self, author: discord.Member, label: str, config_key: str, current_config: dict):
        super().__init__(
            placeholder=f"Select {label}",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )
        self.author = author
        self.label_text = label
        self.config_key = config_key
        self.current_config = current_config

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                embed=NotYourPanel(), ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        
        selected_channel = self.values[0]
        
        # Map config_key to database field name
        key_mapping = {
            "warn_mute_role": "WARN_MUTE_BANREQUEST_ROLE",
            "kick_ban_role": "KICK_BAN_ROLE",
            "whitelist_role": "PUNISHMENT_WHITELIST_ROLE",
            "log_channel": "LOG_CHANNEL_ID",
            "ban_request_channel": "BAN_REQUEST_CHANNEL_ID",
            "action_proofs_channel": "ACTION_PROOFS_CHANNEL_ID",
        }
        
        db_key = key_mapping.get(self.config_key, self.config_key)
        
        try:
            await interaction.client.config.update_one(
                {"_id": interaction.guild.id},
                {
                    "$set": {
                        f"moderation.{db_key}": selected_channel.id
                    }
                },
                upsert=True,
            )
            await interaction.followup.send(
                f"{tick} {self.label_text} set to {selected_channel.mention}",
                ephemeral=True,
            )
        except Exception as e:
            print(f"Error saving channel config: {e}")
            await interaction.followup.send(
                f"{no} Error saving configuration: {str(e)}",
                ephemeral=True,
            )


async def get_moderation_commands_embed():
    """Extract and display all commands from the moderation module"""
    try:
        from Cogs.Modules import moderation
        import inspect
        
        embed = discord.Embed(
            title="📋 Available Moderation Commands",
            description="All commands available in the moderation module:\n",
            color=discord.Colour.dark_embed()
        )
        
        # Find all commands in the PunishmentPanel cog
        cog_class = moderation.PunishmentPanel
        commands_found = []
        
        # Get all methods from the cog
        for name, method in inspect.getmembers(cog_class, predicate=inspect.isfunction):
            # Check if it's a command (has command decorator)
            if hasattr(method, '__name__'):
                # Extract docstring for description
                docstring = inspect.getdoc(method)
                if docstring:
                    first_line = docstring.split('\n')[0]
                    commands_found.append((name, first_line))
        
        # Also get commands from the module-level functions/classes
        command_names = ["warn", "kick", "ban", "timeout", "unban", "banrequest", "case", "modcases", "editcase"]
        command_descriptions = {
            "warn": "Warn users (up to 5) Usage: .warn @user ?r [reason] (alias: .w)",
            "kick": "Kick users (up to 5) Usage: .kick @user ?r [reason] (alias: .k)",
            "ban": "Ban users (up to 5) Usage: .ban @user ?r [reason] (alias: .b)",
            "timeout": "Timeout users for specified duration. Usage: .timeout @user <duration> ?r [reason] (alias: .mute)",
            "unban": "Unban a user. Usage: .unban <user_id>",
            "banrequest": "Request a ban for junior moderators/trial mods. Usage: .banrequest @user <reason> (alias: .br)",
            "case": "View punishment cases by ID or user/all cases. Usage: .case [case_id] or .case [@user] (alias: .c)",
            "modcases": "View modcases you issued or another user's modcases. Usage: .modcases [@user] (alias: .mc)",
            "editcase": "Edit or delete a punishment case. Usage: .editcase <case_id>. (alias: .editc)",
        }
        
        for cmd in command_names:
            desc = command_descriptions.get(cmd, "Moderation command")
            embed.add_field(name=f"**/{cmd}** or **{{prefix}}{cmd}**", value=f"{desc}", inline=False)
        
        embed.set_footer(text="Use /help <command> for more detailed information")
        return embed
        
    except Exception as e:
        print(f"Error loading moderation commands: {e}")
        embed = discord.Embed(
            title="📋 Available Moderation Commands",
            description=(
                "**Punishment Commands:**\n"
                "• `/warn` or `.warn` - Warn users (up to 5)\n"
                "• `/kick` or `.kick` - Kick users (15 per hour limit)\n"
                "• `/ban` or `.ban` - Ban users (15 per hour limit)\n"
                "• `/timeout` or `.timeout` - Timeout users for specified duration\n"
                "• `/unban` or `.unban` - Unban a user\n\n"
                "**Ban Request System:**\n"
                "• `/banrequest` or `.banrequest` - Request a ban for junior moderators\n\n"
                "**Case Management:**\n"
                "• `/case` or `.case` - View punishment cases\n"
                "• `/modcases` or `.modcases` - View modcases (your own or another user's)\n"
                "• `/editcase` or `.editcase` - Edit or delete a case\n"
            ),
            color=discord.Colour.dark_embed()
        )
        embed.set_footer(text="Use /help <command> for more detailed information")
        return embed
