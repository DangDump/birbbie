
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import string
import io
from datetime import datetime, timedelta
from typing import Optional
from utils.emojis import tick, no, greencheck, redx, hammer, page, info, modd, reason as reason_emoji, usr, pen
from utils.HelpEmbeds import (
    BotNotConfigured,
    ModuleNotEnabled,
    Support,
    ModuleNotSetup,
    NotYourPanel,
)
from utils.permissions import has_staff_role, check_admin_and_staff

environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")

# Default Role IDs for permissions (can be overridden by config)
DEFAULT_WARN_MUTE_BANREQUEST_ROLE = 1431769854112698390
DEFAULT_KICK_BAN_ROLE = 1431726641465393162
DEFAULT_PUNISHMENT_WHITELIST_ROLE = 1429167267891118160
DEFAULT_LOG_CHANNEL_ID = 1432451511266578452
DEFAULT_BAN_REQUEST_CHANNEL_ID = 1432451652408971335
DEFAULT_ACTION_PROOFS_CHANNEL_ID = 1447086449462874204

# These will be populated per guild from config
WARN_MUTE_BANREQUEST_ROLE = DEFAULT_WARN_MUTE_BANREQUEST_ROLE
KICK_BAN_ROLE = DEFAULT_KICK_BAN_ROLE
PUNISHMENT_WHITELIST_ROLE = DEFAULT_PUNISHMENT_WHITELIST_ROLE
LOG_CHANNEL_ID = DEFAULT_LOG_CHANNEL_ID
BAN_REQUEST_CHANNEL_ID = DEFAULT_BAN_REQUEST_CHANNEL_ID
ACTION_PROOFS_CHANNEL_ID = DEFAULT_ACTION_PROOFS_CHANNEL_ID


async def get_moderation_config(bot, guild_id: int) -> dict:
    """Get moderation configuration for a guild, returns None if not configured"""
    try:
        config = await bot.config.find_one({"_id": guild_id})
        if config and "moderation" in config:
            mod_config = config["moderation"]
            return {
                "WARN_MUTE_BANREQUEST_ROLE": mod_config.get("WARN_MUTE_BANREQUEST_ROLE"),
                "KICK_BAN_ROLE": mod_config.get("KICK_BAN_ROLE"),
                "PUNISHMENT_WHITELIST_ROLE": mod_config.get("PUNISHMENT_WHITELIST_ROLE"),
                "LOG_CHANNEL_ID": mod_config.get("LOG_CHANNEL_ID"),
                "BAN_REQUEST_CHANNEL_ID": mod_config.get("BAN_REQUEST_CHANNEL_ID"),
                "ACTION_PROOFS_CHANNEL_ID": mod_config.get("ACTION_PROOFS_CHANNEL_ID"),
            }
    except Exception as e:
        print(f"Error loading moderation config: {e}")
    
    # Return None if no config found
    return None


async def check_moderation_config(ctx: commands.Context) -> tuple[bool, str]:
    """Check if moderation is properly configured for the guild"""
    config = await get_moderation_config(ctx.bot, ctx.guild.id)
    
    if not config:
        return False, f"{no} Moderation is not configured for this server. Please ask an admin to configure it in the config menu."
    
    # Check required roles
    if not config.get("WARN_MUTE_BANREQUEST_ROLE") or not config.get("KICK_BAN_ROLE") or not config.get("PUNISHMENT_WHITELIST_ROLE"):
        return False, f"{no} Moderation roles are not properly configured. Please ask an admin to configure them in the config menu."
    
    return True, ""


async def check_logging_channels(ctx: commands.Context, config: dict) -> str:
    """Check if logging channels are configured and return warning if not"""
    warnings = []
    
    if not config.get("LOG_CHANNEL_ID"):
        warnings.append(f"{no} Warning: Punishment log channel is not configured. Logs won't be saved.")
    
    if not config.get("BAN_REQUEST_CHANNEL_ID"):
        warnings.append(f"{no} Warning: Ban request channel is not configured. Ban requests won't work.")
    
    if not config.get("ACTION_PROOFS_CHANNEL_ID"):
        warnings.append(f"{no} Warning: Action proofs channel is not configured. Proof attachments won't work.")
    
    return "\n".join(warnings) if warnings else ""


# Check functions for permissions (used in decorators) - these must be SILENT
async def has_warn_mute_role(ctx: commands.Context) -> bool:
    """Check if user has WARN_MUTE_BANREQUEST_ROLE - silent check for decorator"""
    try:
        config = await get_moderation_config(ctx.bot, ctx.guild.id)
        # If config doesn't exist, return True to let command handle the error
        if not config:
            return True
        # If config exists but role is not set, still return True
        if not config.get("WARN_MUTE_BANREQUEST_ROLE"):
            return True
        # Only check the role if config exists
        return any(role.id == config.get("WARN_MUTE_BANREQUEST_ROLE") for role in ctx.author.roles)
    except:
        return True


async def has_kick_ban_role(ctx: commands.Context) -> bool:
    """Check if user has KICK_BAN_ROLE - silent check for decorator"""
    try:    
        config = await get_moderation_config(ctx.bot, ctx.guild.id)
        # If config doesn't exist, return True to let command handle the error
        if not config:
            return True
        # If config exists but role is not set, still return True
        if not config.get("KICK_BAN_ROLE"):
            return True
        # Only check the role if config exists
        return any(role.id == config.get("KICK_BAN_ROLE") for role in ctx.author.roles)
    except:
        return True


class PunishmentModal(discord.ui.Modal, title="Issue Punishment"):
    """Modal for entering user ID and punishment reason"""

    def __init__(self, punishment_type: str, issuer_id: int, cog):
        super().__init__()
        self.punishment_type = punishment_type
        self.issuer_id = issuer_id
        self.cog = cog

    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter the user's Discord ID",
        style=discord.TextStyle.short,
        required=True,
        min_length=1,
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter the punishment reason",
        style=discord.TextStyle.long,
        required=True,
        min_length=1,
    )

    duration = discord.ui.TextInput(
        label="Duration (for timeout)",
        placeholder="e.g., 1h, 30m, 1d (leave empty if not applicable)",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        try:
            target_user_id = int(self.user_id.value)
        except ValueError:
            try:
                await interaction.followup.send(
                    f"{no} Invalid user ID. Please enter a valid number.",
                    ephemeral=True,
                )
            except Exception:
                pass
            return

        try:
            # Check if target user is whitelisted
            try:
                target_member = await interaction.guild.fetch_member(target_user_id)
                is_whitelisted = (
                    target_member.guild_permissions.administrator or
                    any(role.id == PUNISHMENT_WHITELIST_ROLE for role in target_member.roles)
                )
                if is_whitelisted:
                    await interaction.followup.send(
                        f"{no} Can't punish this person!",
                        ephemeral=True,
                    )
                    return
            except discord.NotFound:
                # User not in guild, allow punishment
                pass
            # Generate punishment ID
            punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

            # Create punishment record
            punishment_data = {
                "punishment_id": punishment_id,
                "guild_id": interaction.guild.id,
                "target_user_id": target_user_id,
                "punishment_type": self.punishment_type,
                "reason": self.reason.value,
                "issuer_id": self.issuer_id,
                "timestamp": datetime.now(),
                "proofs": [],
            }

            # Add duration if timeout
            if self.punishment_type == "timeout" and self.duration.value:
                punishment_data["duration"] = self.duration.value

            # Save to database
            await interaction.client.qdb["punishments"].insert_one(punishment_data)
            # quota counter 999
            try:
                await interaction.client.qdb["modcases"].update_one(
                    {"guild_id": interaction.guild.id, "user_id": target_user_id},
                    {"$inc": {"modcase_count": 1}},
                    upsert=True,
                )
            except Exception:
                pass

            # Create embed for logging
            embed = discord.Embed(
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(),
            )
            embed.set_author(name=f"Punishment Issued", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
            duration_text = f"\n> Duration: {self.duration.value}" if self.punishment_type == "timeout" and self.duration.value else ""
            embed.description = (
                f"**Punishment Type:** {self.punishment_type.title()}\n\n"
                f"> Target User: <@{target_user_id}>\n"
                f"> Punished User ID: `{target_user_id}`\n"
                f"> Reason: {self.reason.value}"
                f"{duration_text}\n"
                f"> Issuer: <@{self.issuer_id}>"
            )
            embed.set_footer(
                text=f"Punishment ID: {punishment_id}",
                icon_url=interaction.user.display_avatar,
            )

            # No thumbnail or bottom banner here — keep punishment logs image-free

            # Log to channel asynchronously without awaiting
            async def log_punishment():
                try:
                    log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(embed=embed)
                except Exception as e:
                    print(f"Error logging punishment: {e}")

            # Schedule the logging as a background task
            interaction.client.loop.create_task(log_punishment())

            # Execute the punishment action
            try:
                target_member = None
                try:
                    target_member = await interaction.guild.fetch_member(target_user_id)
                except discord.NotFound:
                    pass


                if self.punishment_type == "warn":
                    # Warn action - send DM to user
                    try:
                        target_user = await interaction.client.fetch_user(target_user_id)
                        dm_embed = discord.Embed(
                            title=f"<:Alert:1447279662517583923> You have been warned in **{interaction.guild.name}**.",
                            description=f"> Moderator: <@{self.issuer_id}>\n> Reason: **{self.reason.value}**",
                            color=discord.Color.from_rgb(255, 0, 0),
                            timestamp=datetime.now()
                        )
                        dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.",icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
                        await target_user.send(embed=dm_embed)
                    except Exception:
                        pass

                elif self.punishment_type == "timeout":
                    # Timeout action
                    if target_member and self.duration.value:
                        try:
                            # Parse duration
                            duration_str = self.duration.value.lower()
                            duration_seconds = 0
                            
                            if "h" in duration_str:
                                hours = int(duration_str.replace("h", "").strip())
                                duration_seconds = hours * 3600
                            elif "m" in duration_str:
                                minutes = int(duration_str.replace("m", "").strip())
                                duration_seconds = minutes * 60
                            elif "d" in duration_str:
                                days = int(duration_str.replace("d", "").strip())
                                duration_seconds = days * 86400
                            
                            if duration_seconds > 0:
                                from datetime import timedelta
                                # DM user before applying timeout
                                try:
                                    target_user = await interaction.client.fetch_user(target_user_id)
                                    dm_embed = discord.Embed(
                                        title=f"⏱️ You have been timed out in **{interaction.guild.name}**.",
                                        description=f"> Moderator: <@{self.issuer_id}>\n> Reason: **{self.reason.value}**",
                                        color=discord.Color.from_rgb(255, 0, 0),
                                        timestamp=datetime.now()
                                    )
                                    dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.",icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
                                    await target_user.send(embed=dm_embed)
                                except Exception:
                                    pass

                                await target_member.timeout(timedelta(seconds=duration_seconds), reason=self.reason.value)
                        except Exception as e:
                            print(f"Error applying timeout: {e}")

                elif self.punishment_type == "kick":
                    # Kick action
                    if target_member:
                        try:
                            # DM user before kick
                            try:
                                target_user = await interaction.client.fetch_user(target_user_id)
                                dm_embed = discord.Embed(
                                    title=f"👢 You have been kicked from **{interaction.guild.name}**.",
                                    description=f"> Moderator: <@{self.issuer_id}>\n> Reason: **{self.reason.value}**",
                                    color=discord.Color.from_rgb(255, 0, 0),
                                    timestamp=datetime.now()
                                )
                                dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.",icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
                                await target_user.send(embed=dm_embed)
                            except Exception:
                                pass

                            await target_member.kick(reason=self.reason.value)
                        except Exception as e:
                            print(f"Error kicking member: {e}")

                elif self.punishment_type == "ban":
                    # Ban action
                    try:
                        # DM user before ban
                        try:
                            target_user = await interaction.client.fetch_user(target_user_id)
                            dm_embed = discord.Embed(
                                title=f"🔨 You have been banned from **{interaction.guild.name}**.",
                                description=f"> Moderator: <@{self.issuer_id}>\n> Reason: **{self.reason.value}**",
                                color=discord.Color.from_rgb(255, 0, 0),
                                timestamp=datetime.now()
                            )
                            dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
                            await target_user.send(embed=dm_embed)
                        except Exception:
                            pass

                        await interaction.guild.ban(discord.Object(target_user_id), reason=self.reason.value)
                    except Exception as e:
                        print(f"Error banning member: {e}")

                elif self.punishment_type == "request_ban":
                    # Request ban - send to ban request channel
                    try:
                        ban_request_channel = interaction.client.get_channel(BAN_REQUEST_CHANNEL_ID)
                        if ban_request_channel:
                            ban_embed = discord.Embed(
                                title=f"Ban Request | {punishment_id}",
                                color=discord.Color.orange(),
                                timestamp=datetime.now(),
                            )
                            ban_embed.set_author(name=f"Ban Request | {punishment_id}", icon_url="https://cdn.discordapp.com/attachments/1432452094019915800/1432452119627329648/image_2.png")
                            ban_embed.add_field(name="Target User", value=f"<@{target_user_id}>", inline=False)
                            ban_embed.add_field(name="User ID", value=f"`{target_user_id}`", inline=False)
                            ban_embed.add_field(name="Reason", value=self.reason.value, inline=False)
                            ban_embed.add_field(name="Requested by", value=f"<@{self.issuer_id}>", inline=False)
                            ban_embed.set_footer(text=f"Punishment ID: {punishment_id}")
                            
                            view = BanRequestView(punishment_id, target_user_id, self.reason.value, self.issuer_id)
                            await ban_request_channel.send(embed=ban_embed, view=view)
                    except Exception as e:
                        print(f"Error sending ban request: {e}")

            except Exception as e:
                print(f"Error executing punishment: {e}")

            try:
                if self.punishment_type == "timeout":
                    action_text = "timed out"
                elif self.punishment_type == "ban":
                    action_text = "banned"
                elif self.punishment_type == "request_ban":
                    action_text = "requested ban for"
                else:
                    action_text = f"{self.punishment_type}ed"
                # Single-target modal: show formatted success message as an embed
                try:
                    guild_icon = None
                    if interaction.guild and interaction.guild.icon:
                        guild_icon = interaction.guild.icon.url
                    success_embed = discord.Embed(
                        description=(
                            f"**{tick} Successfully {action_text} <@{target_user_id}>.**\n"
                            f"> {modd} Moderator: <@{self.issuer_id}>\n"
                            f"> {reason_emoji} Reason: {self.reason.value}\n"
                        ),
                        color=discord.Color.from_rgb(54, 57, 63),
                        timestamp=datetime.now(),
                    )
                    success_embed.set_footer(text=f"Punishment ID: {punishment_id}", icon_url=guild_icon)
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                except Exception:
                    # Fall back silently if embed send fails
                    pass
            except Exception:
                pass

            # Also send a message with an Attach Proofs button so issuer can upload files
            try:
                guild_icon = None
                if interaction.guild and interaction.guild.icon:
                    guild_icon = interaction.guild.icon.url
                attach_embed = discord.Embed(
                    description=f"{tick} Click the button below to attach proofs to this case: `{punishment_id}`",
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=datetime.now(),
                )
                attach_embed.set_footer(text=f"Punished User ID : {target_user_id}", icon_url=guild_icon)
                await interaction.followup.send(embed=attach_embed, view=AttachProofsView(punishment_id, self.cog), ephemeral=True)
            except Exception:
                pass
        except Exception as e:
            print(f"Error in punishment modal: {e}")
            try:
                await interaction.followup.send(
                    f"{no} An error occurred: {str(e)}",
                    ephemeral=True,
                )
            except Exception:
                pass


class BanRequestView(discord.ui.View):
    """View for ban request approval/denial"""

    def __init__(self, punishment_id: str, target_user_id: int, reason: str, issuer_id: int):
        super().__init__(timeout=None)
        self.punishment_id = punishment_id
        self.target_user_id = target_user_id
        self.reason = reason
        self.issuer_id = issuer_id

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.red, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has KICK_BAN_ROLE
        user_roles = [role.id for role in interaction.user.roles]
        if KICK_BAN_ROLE not in user_roles:
            await interaction.response.send_message(
                f"{no} You don't have permission to approve bans.",
                ephemeral=True,
            )
            return

        try:
            # DM user before banning
            try:
                target_user = await interaction.client.fetch_user(self.target_user_id)
                dm_embed = discord.Embed(
                    title="🔨 You have been banned",
                    description=f"**Guild:** {interaction.guild.name}\n\n**Reason:**\n{self.reason}",
                    color=discord.Color.from_rgb(255, 0, 0),
                    timestamp=datetime.now()
                )
                await target_user.send(embed=dm_embed)
            except Exception:
                pass

            await interaction.guild.ban(discord.Object(self.target_user_id), reason=f"Ban request approved by {interaction.user.name}: {self.reason}")
            await interaction.response.send_message(
                f"{tick} User has been banned.",
                ephemeral=True,
            )
            # Update punishment record
            await interaction.client.qdb["punishments"].update_one(
                {"punishment_id": self.punishment_id},
                {"$set": {"punishment_type": "ban", "approved_by": interaction.user.id}},
            )
            # Edit the message to show it was approved
            await interaction.message.edit(content=f"{greencheck} Ban approved by <@{interaction.user.id}>", view=None)
        except Exception as e:
            print(f"Error banning user: {e}")
            await interaction.response.send_message(
                f"{no} Error banning user: {str(e)}",
                ephemeral=True,
            )

    @discord.ui.button(label="Abort", style=discord.ButtonStyle.grey, emoji="❌")
    async def abort_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has KICK_BAN_ROLE
        user_roles = [role.id for role in interaction.user.roles]
        if KICK_BAN_ROLE not in user_roles:
            await interaction.response.send_message(
                f"{no} You don't have permission to abort bans.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{tick} Ban request aborted.",
            ephemeral=True,
        )
        # Edit the message to show it was aborted
        await interaction.message.edit(content=f"{redx} Ban aborted by <@{interaction.user.id}>", view=None)


class AttachProofsView(discord.ui.View):
    """View with button to attach proofs"""

    def __init__(self, punishment_id: str, cog):
        super().__init__(timeout=None)
        self.punishment_id = punishment_id
        self.cog = cog

    @discord.ui.button(label="Attach Proofs", style=discord.ButtonStyle.green)
    async def attach_proofs(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Attach proofs via the central action-proofs channel flow.
        try:
            # Verify punishment exists and permission
            punishment = await interaction.client.qdb["punishments"].find_one({"punishment_id": self.punishment_id})
            if not punishment:
                await interaction.response.send_message(f"{no} Punishment ID not found.", ephemeral=True)
                return

            # Only allow the original issuer to attach proofs
            if punishment.get("issuer_id") != interaction.user.id:
                await interaction.response.send_message(f"{no} You can only attach proofs to your own punishments.", ephemeral=True)
                return

            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                pass

            action_ch = interaction.client.get_channel(ACTION_PROOFS_CHANNEL_ID)
            if not action_ch:
                # fallback to existing handler if channel not available
                try:
                    await self.cog.attach_proofs(interaction, self.punishment_id)
                except Exception as e:
                    print(f"Error falling back to attach_proofs: {e}")
                    try:
                        await interaction.response.send_message(f"{no} An error occurred.", ephemeral=True)
                    except Exception:
                        pass
                return

            # Create an instruction message in the action channel
            try:
                instr = await action_ch.send(
                    f"{interaction.user.mention} Please upload your proof image(s) as a reply to this message for punishment `{self.punishment_id}`."
                )
            except Exception as e:
                print(f"Failed to create instruction message in action proofs channel: {e}")
                await interaction.response.send_message(f"{no} Could not post instruction in proofs channel.", ephemeral=True)
                return

            # Inform user with ephemeral message
            try:
                await interaction.followup.send(
                    f"{tick} I've created a message in <#{ACTION_PROOFS_CHANNEL_ID}> - please reply to that message with your image proofs. Jump: {instr.jump_url}",
                    ephemeral=True,
                )
            except Exception:
                pass

            # Wait for the user's reply in the action proofs channel
            def check(msg: discord.Message):
                # Accept replies by the same user in the action channel that reference our instruction message and include attachments
                if msg.author != interaction.user:
                    return False
                if msg.channel.id != ACTION_PROOFS_CHANNEL_ID:
                    return False
                if not msg.attachments:
                    return False
                # If message is a reply to our instruction message or references it
                if msg.reference and getattr(msg.reference, 'message_id', None) == instr.id:
                    return True
                # also allow direct replies without reference (less strict)
                return False

            try:
                proof_message = await interaction.client.wait_for("message", check=check, timeout=600)
            except Exception:
                await action_ch.send(f"{interaction.user.mention} Proof upload timed out for punishment `{self.punishment_id}`.")
                return

            # Read attachment bytes so we can both upload to the log and show an ephemeral preview
            attachment_blobs = []  # list of (filename, bytes)
            for att in proof_message.attachments:
                try:
                    data = await att.read()
                    attachment_blobs.append((att.filename, data))
                except Exception as ex:
                    print(f"Failed to read attachment {att.filename} for log upload: {ex}")

            # Find original log message in log channel and reply there with files
            try:
                log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    found = False
                    async for message in log_channel.history(limit=500):
                        if message.embeds:
                            for embed in message.embeds:
                                footer_text = embed.footer.text if embed.footer else None
                                if footer_text and self.punishment_id in footer_text:
                                    try:
                                        # Build files for log upload
                                        files_for_log = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]

                                        if files_for_log:
                                            new_msg = await message.reply(files=files_for_log)
                                        else:
                                            new_msg = await message.reply(content=f"Proofs for punishment `{self.punishment_id}`")

                                        uploaded_urls = [a.url for a in new_msg.attachments]

                                        await interaction.client.qdb["punishments"].update_one({"punishment_id": self.punishment_id}, {"$set": {"proofs": uploaded_urls}})

                                        try:
                                            orig_edited = discord.Embed.from_dict(embed.to_dict())
                                        except Exception:
                                            orig_edited = embed
                                        orig_edited.add_field(name="Attached Proofs", value=f"[View proofs here]({new_msg.jump_url})", inline=False)
                                        await message.edit(embed=orig_edited)
                                    except Exception as e:
                                        print(f"Error replying with attachments to log message: {e}")
                                    found = True
                                    break
                        if found:
                            break
            except Exception as e:
                print(f"Error updating log message via action channel flow: {e}")

            # Also reply to ban request message if this is a request_ban
            try:
                punishment = await interaction.client.qdb["punishments"].find_one({"punishment_id": self.punishment_id})
                if punishment and punishment.get("punishment_type") == "request_ban":
                    ban_request_channel = interaction.client.get_channel(BAN_REQUEST_CHANNEL_ID)
                    if ban_request_channel:
                        found = False
                        async for message in ban_request_channel.history(limit=500):
                            if message.embeds:
                                for embed in message.embeds:
                                    footer_text = embed.footer.text if embed.footer else None
                                    if footer_text and self.punishment_id in footer_text:
                                        try:
                                            files_for_request = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]
                                            if files_for_request:
                                                await message.reply(files=files_for_request)
                                        except Exception as e:
                                            print(f"Error replying with attachments to ban request message: {e}")
                                        found = True
                                        break
                            if found:
                                break
            except Exception as e:
                print(f"Error updating ban request message: {e}")

            # Acknowledge to action channel and also send ephemeral preview to the user
            try:
                await action_ch.send(f"{tick} {interaction.user.mention} Proof image(s) attached successfully for `{self.punishment_id}`.")
            except Exception:
                pass

            # Send ephemeral preview of the uploaded images back to the user
            try:
                if attachment_blobs:
                    ephemeral_files = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]
                    await interaction.followup.send(f"{tick} Here is a preview of the image(s) you uploaded for `{self.punishment_id}`:", files=ephemeral_files, ephemeral=True)
                else:
                    await interaction.followup.send(f"{tick} Proofs attached successfully!", ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send(f"{tick} Proofs attached successfully!", ephemeral=True)
                except Exception:
                    pass

            # Optionally delete user's proof message to keep the channel tidy
            try:
                await proof_message.delete()
            except Exception:
                pass

            return
        except Exception as e:
            print(f"Error in AttachProofsView.attach_proofs: {e}")
            try:
                await interaction.response.send_message(f"{no} An error occurred.", ephemeral=True)
            except Exception:
                pass


class AttachProofsSelect(discord.ui.Select):
    """Dropdown for selecting which punishment to attach proofs to"""

    def __init__(self, punishment_ids: dict, cog):
        """
        punishment_ids: dict with punishment_id as key and user_id as value
        """
        self.punishment_ids = punishment_ids
        self.cog = cog
        
        options = [
            discord.SelectOption(label=f"Attach to punishment {pid}", value=pid)
            for pid in punishment_ids.keys()
        ]
        super().__init__(
            placeholder="Select a punishment to attach proofs to",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            punishment_id = self.values[0]
            # Ensure only the issuer can attach proofs via the select flow
            punishment = await interaction.client.qdb["punishments"].find_one({"punishment_id": punishment_id})
            if not punishment:
                await interaction.response.send_message(f"{no} Punishment ID not found.", ephemeral=True)
                return
            if punishment.get("issuer_id") != interaction.user.id:
                await interaction.response.send_message(f"{no} You can only attach proofs to your own punishments.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            
            action_ch = interaction.client.get_channel(ACTION_PROOFS_CHANNEL_ID)
            if not action_ch:
                await interaction.followup.send(f"{no} Action proofs channel not found.", ephemeral=True)
                return

            # Create instruction message in action channel
            try:
                instr = await action_ch.send(
                    f"{interaction.user.mention} Please upload your proof image(s) as a reply to this message for punishment `{punishment_id}`."
                )
            except Exception as e:
                print(f"Failed to create instruction message: {e}")
                await interaction.followup.send(f"{no} Could not post instruction in proofs channel.", ephemeral=True)
                return

            # Inform user with jump link
            try:
                await interaction.followup.send(
                    f"{tick} I've created a message in <#{ACTION_PROOFS_CHANNEL_ID}> - please reply to that message with your image proofs. Jump: {instr.jump_url}",
                    ephemeral=True,
                )
            except Exception:
                pass

            # Wait for user's reply with attachments
            def check(msg: discord.Message):
                if msg.author != interaction.user:
                    return False
                if msg.channel.id != ACTION_PROOFS_CHANNEL_ID:
                    return False
                if not msg.attachments:
                    return False
                if msg.reference and getattr(msg.reference, 'message_id', None) == instr.id:
                    return True
                return False

            try:
                proof_message = await interaction.client.wait_for("message", check=check, timeout=600)
            except Exception:
                await action_ch.send(f"{interaction.user.mention} Proof upload timed out for punishment `{punishment_id}`.")
                return

            # Read attachment bytes so we can both upload to the log and show an ephemeral preview
            attachment_blobs = []
            for att in proof_message.attachments:
                try:
                    data = await att.read()
                    attachment_blobs.append((att.filename, data))
                except Exception as ex:
                    print(f"Failed to prepare attachment {att.filename}: {ex}")

            # Find original log message in log channel and reply there with files
            try:
                log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    found = False
                    async for message in log_channel.history(limit=500):
                        if message.embeds:
                            for embed in message.embeds:
                                footer_text = embed.footer.text if embed.footer else None
                                if footer_text and punishment_id in footer_text:
                                    try:
                                        files_for_log = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]

                                        if files_for_log:
                                            new_msg = await message.reply(files=files_for_log)
                                        else:
                                            new_msg = await message.reply(content=f"Proofs for punishment `{punishment_id}`")

                                        uploaded_urls = [a.url for a in new_msg.attachments]
                                        await interaction.client.qdb["punishments"].update_one(
                                            {"punishment_id": punishment_id},
                                            {"$set": {"proofs": uploaded_urls}},
                                        )

                                        try:
                                            orig_edited = discord.Embed.from_dict(embed.to_dict())
                                        except Exception:
                                            orig_edited = embed
                                        orig_edited.add_field(name="Attached Proofs", value=f"[View proofs here]({new_msg.jump_url})", inline=False)
                                        await message.edit(embed=orig_edited)
                                    except Exception as e:
                                        print(f"Error replying with attachments: {e}")
                                    found = True
                                    break
                        if found:
                            break
            except Exception as e:
                print(f"Error updating log message: {e}")

            # Also reply to ban request message if this is a request_ban
            try:
                punishment = await interaction.client.qdb["punishments"].find_one({"punishment_id": punishment_id})
                if punishment and punishment.get("punishment_type") == "request_ban":
                    ban_request_channel = interaction.client.get_channel(BAN_REQUEST_CHANNEL_ID)
                    if ban_request_channel:
                        found = False
                        async for message in ban_request_channel.history(limit=500):
                            if message.embeds:
                                for embed in message.embeds:
                                    footer_text = embed.footer.text if embed.footer else None
                                    if footer_text and punishment_id in footer_text:
                                        try:
                                            files_for_request = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]
                                            if files_for_request:
                                                await message.reply(files=files_for_request)
                                        except Exception as e:
                                            print(f"Error: {e}")
                                        found = True
                                        break
                            if found:
                                break
            except Exception as e:
                print(f"Error updating ban request message: {e}")

            # Acknowledge in action channel
            try:
                await action_ch.send(f"{tick} {interaction.user.mention} Proof image(s) attached successfully for `{punishment_id}`.")
            except Exception:
                pass

            # Send ephemeral preview back to the user
            try:
                if attachment_blobs:
                    ephemeral_files = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]
                    await interaction.followup.send(f"{tick} Here is a preview of the image(s) you uploaded for `{punishment_id}`:", files=ephemeral_files, ephemeral=True)
                else:
                    await interaction.followup.send(f"{tick} Proofs attached successfully!", ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send(f"{tick} Proofs attached successfully!", ephemeral=True)
                except Exception:
                    pass

            try:
                await proof_message.delete()
            except Exception:
                pass

        except Exception as e:
            print(f"Error in AttachProofsSelect: {e}")
            try:
                await interaction.followup.send(f"{no} An error occurred.", ephemeral=True)
            except Exception:
                pass


class AttachProofsSelectView(discord.ui.View):
    """View containing the punishment select dropdown"""

    def __init__(self, punishment_ids: dict, cog):
        super().__init__(timeout=None)
        self.add_item(AttachProofsSelect(punishment_ids, cog))


class PunishmentTypeSelect(discord.ui.Select):
    """Dropdown for selecting punishment type"""

    def __init__(self, cog, issuer_id: int):
        self.cog = cog
        self.issuer_id = issuer_id
        options = [
            discord.SelectOption(label="None", value="none", emoji="❌", description="Click here to reselect an option."),
            discord.SelectOption(label="Warn", value="warn", emoji="⚠️"),
            discord.SelectOption(label="Timeout", value="timeout", emoji="⏱️"),
            discord.SelectOption(label="Kick", value="kick", emoji="👢"),
            discord.SelectOption(label="Ban", value="ban", emoji="🔨"),
            discord.SelectOption(label="Request Ban", value="request_ban", emoji="🚫"),
        ]
        super().__init__(
            placeholder="Select a punishment type",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            punishment_type = self.values[0]

            # None option does nothing
            if punishment_type == "none":
                await interaction.response.defer()
                return

            # Check role permissions
            user_roles = [role.id for role in interaction.user.roles]
            
            if punishment_type in ["warn", "timeout"]:
                if WARN_MUTE_BANREQUEST_ROLE not in user_roles:
                    await interaction.response.send_message(
                        f"{no} You don't have permission to issue {punishment_type}s.",
                        ephemeral=True,
                    )
                    return
            elif punishment_type in ["request_ban"]:
                # WARN_MUTE_BANREQUEST_ROLE can request bans
                if not any(role.id in [WARN_MUTE_BANREQUEST_ROLE, KICK_BAN_ROLE] for role in interaction.user.roles):
                    await interaction.response.send_message(
                        f"{no} You don't have permission to request bans.",
                        ephemeral=True,
                    )
                    return
            elif punishment_type in ["kick", "ban"]:
                if KICK_BAN_ROLE not in user_roles:
                    await interaction.response.send_message(
                        f"{no} You don't have permission to {punishment_type} users.",
                        ephemeral=True,
                    )
                    return

            # Show modal for punishment form
            modal = PunishmentModal(punishment_type, self.issuer_id, self.cog)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in punishment type select: {e}")
            try:
                await interaction.response.send_message(
                    f"{no} An error occurred: {str(e)}",
                    ephemeral=True,
                )
            except Exception:
                pass

class PunishmentPanelView(discord.ui.View):
    """View containing the punishment type dropdown"""

    def __init__(self, cog, issuer_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.issuer_id = issuer_id
        self.add_item(PunishmentTypeSelect(cog, issuer_id))


class PunishmentPanel(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        # Rate limiting: {user_id: {"kick": [], "ban": []}} where lists contain timestamps
        self.punishment_tracker = {}

    async def load_guild_config(self, guild_id: int):
        """Load and cache moderation config for a guild"""
        return await get_moderation_config(self.client, guild_id)

    def check_punishment_limit(self, user_id: int, punishment_type: str, limit: int = 15, hours: int = 1) -> tuple[bool, int]:
        """
        Check if user has exceeded punishment limit per hour.
        Returns: (is_allowed: bool, remaining_count: int)
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=hours)
        
        if user_id not in self.punishment_tracker:
            self.punishment_tracker[user_id] = {"kick": [], "ban": []}
        
        # Clean up old timestamps
        self.punishment_tracker[user_id][punishment_type] = [
            ts for ts in self.punishment_tracker[user_id][punishment_type] 
            if ts > hour_ago
        ]
        
        count = len(self.punishment_tracker[user_id][punishment_type])
        remaining = limit - count
        
        return remaining > 0, remaining

    def add_punishment_record(self, user_id: int, punishment_type: str):
        """Record a punishment action"""
        if user_id not in self.punishment_tracker:
            self.punishment_tracker[user_id] = {"kick": [], "ban": []}
        
        self.punishment_tracker[user_id][punishment_type].append(datetime.now())

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Cog-level error handler to provide clearer messages for common failures."""
        try:
            # Unwrap CommandInvokeError to original
            if isinstance(error, commands.CommandInvokeError) and error.original:
                err = error.original
            else:
                err = error

            # Common user-facing errors
            if isinstance(err, commands.BadArgument):
                await ctx.send(f"{no} Invalid argument: {str(err)}")
                return
            if isinstance(err, commands.MissingRequiredArgument):
                await ctx.send(f"{no} Missing required argument: `{err.param.name}`")
                return
            if isinstance(err, commands.CheckFailure):
                await ctx.send(f"{no} You don't have permission to use this command.")
                return

            # Fallback: log traceback and show concise error to channel
            import traceback
            traceback.print_exception(type(err), err, err.__traceback__)
            await ctx.send(f"{no} An error occurred: {type(err).__name__} - {str(err)}")
        except Exception as e:
            # If the error handler itself fails, print and ignore
            print(f"Error in cog_command_error: {e}")

    @commands.hybrid_command(name="warn", aliases=["w"])
    @app_commands.describe(users="Users to warn (up to 5)", reason="Reason for the warning")
    @commands.check(has_warn_mute_role)
    async def warn_cmd(self, ctx: commands.Context, users: commands.Greedy[discord.User], *, reason: str = None):
        """Warn users"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("WARN_MUTE_BANREQUEST_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to warn users.")
                return
            
            # Limit to 5 users
            users = users[:5] if users else []
            if not users:
                await ctx.send(f"{no} Please specify at least one user to warn.")
                return
            
            # Parse reason for prefix commands (extract after ?r)
            final_reason = "No reason given"
            if reason:
                if "?r" in reason:
                    parts = reason.split("?r", 1)
                    final_reason = parts[1].strip() if len(parts) > 1 else "No reason given"
                elif reason.strip():
                    final_reason = reason.strip()
            
            results = []
            created_ids = []

            for target in users:
                try:
                    punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    punishment_data = {
                        "punishment_id": punishment_id,
                        "guild_id": ctx.guild.id,
                        "target_user_id": target.id,
                        "punishment_type": "warn",
                        "reason": final_reason,
                        "issuer_id": ctx.author.id,
                        "timestamp": datetime.now(),
                        "proofs": [],
                    }
                    await ctx.bot.qdb["punishments"].insert_one(punishment_data)
                    # Increment modcases quota counter for this guild/user
                    try:
                        await ctx.bot.qdb["modcases"].update_one(
                            {"guild_id": ctx.guild.id, "user_id": target.id},
                            {"$inc": {"modcase_count": 1}},
                            upsert=True,
                        )
                    except Exception as e:
                        print(f"Error updating quota for warn: {e}")

                    # Send DM to user (best-effort)
                    try:
                        dm_embed = discord.Embed(
                            title=f"<:Alert:1447279662517583923> You have been warned in **{ctx.guild.name}**.",
                            description=f"> Moderator: <@{ctx.author.id}>\n> Reason: **{final_reason}**",
                            color=discord.Color.from_rgb(255, 0, 0),
                            timestamp=datetime.now()
                        )
                        dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                        await target.send(embed=dm_embed)

                    except Exception:
                        pass

                    # Log to channel (embed description)
                    try:
                        log_channel = ctx.bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            embed = discord.Embed(
                                color=discord.Color.from_rgb(54, 57, 63),
                                timestamp=datetime.now(),
                            )
                            embed.set_author(name=f"Punishment Issued", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            embed.description = (
                                f"**Punishment Type:** Warn\n\n"
                                f"> Target User: <@{target.id}>\n"
                                f"> Punished User ID: `{target.id}`\n"
                                f"> Reason: {final_reason}\n"
                                f"> Issuer: <@{ctx.author.id}>"
                            )
                            embed.set_footer(text=f"Punishment ID: {punishment_id}", icon_url=ctx.author.display_avatar)
                            await log_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error logging punishment: {e}")

                    results.append((target, True, punishment_id))
                    created_ids.append(punishment_id)
                except Exception as e:
                    results.append((target, False, str(e)))

            # Build summary embed
            try:
                guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                ids_text = ", ".join([f"`{r[2]}`" for r in results if r[1]]) or "None"
                success_count = sum(1 for r in results if r[1])
                # Use green for successes, red for all failures
                embed_color = discord.Color.from_rgb(102, 255, 0) if success_count > 0 else discord.Color.from_rgb(255, 0, 0)
                embed = discord.Embed(
                    description=(
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {final_reason}\n"
                        f"> {usr} Punishment ID(s): {ids_text}"
                    ),
                    color=embed_color,
                    timestamp=datetime.now(),
                )

                # Add successful list
                success_lines = []
                fail_lines = []
                for target, ok, punishment_id in results:
                    if ok:
                        success_lines.append(f"> {usr} <@{target.id}> (`{punishment_id}`)")
                    else:
                        fail_lines.append(f"{redx} <@{target.id}> — {punishment_id}")

                if success_lines:
                    embed.add_field(name=f"{greencheck} Warned:", value="\n".join(success_lines), inline=False)
                if fail_lines:
                    embed.add_field(name="Failures:", value="\n".join(fail_lines), inline=False)

                embed.set_author(name=f"Warn Result", icon_url=ctx.bot.user.display_avatar.url if ctx.bot.user else None)
                embed.set_footer(text=f"All tasks completed", icon_url=guild_icon)
                
                # Create Attach Proofs view only if there were successful punishments
                punishment_ids = {r[2]: r[0].id for r in results if r[1]}  # {punishment_id: user_id}
                
                if punishment_ids:
                    if len(punishment_ids) == 1:
                        # Single punishment - use single AttachProofsView
                        single_id = list(punishment_ids.keys())[0]
                        view = AttachProofsView(single_id, self)
                    else:
                        # Multiple punishments - use dropdown
                        view = AttachProofsSelectView(punishment_ids, self)
                    
                    # Add guidance message
                    embed.add_field(name=f"{pen} Add Proofs", value=f"Click the button/dropdown below to start adding proofs to this case.", inline=False)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
                
                # Check for missing logging channels and send warnings
                channel_warnings = await check_logging_channels(ctx, config)
                if channel_warnings:
                    await ctx.send(channel_warnings)
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="editcase", aliases=["editc"])
    async def editcase(self, ctx: commands.Context, punishment_id: str):
        """Edit a punishment case's reason or delete the case. Staff only."""
        try:
            # Permission check: staff role
            if not await has_staff_role(ctx):
                return

            punishment = await ctx.bot.qdb["punishments"].find_one({"punishment_id": punishment_id, "guild_id": ctx.guild.id})
            if not punishment:
                await ctx.send(f"{no} Punishment ID `{punishment_id}` not found.")
                return

            # Build embed showing current case
            embed = discord.Embed(
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(),
            )
            embed.set_author(
                name=f"Editing Case: {punishment_id}",
                icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            )
            embed.description = (
                f"> Punishment Type: {punishment.get('punishment_type', 'Unknown')}\n"
                f"> Target User: <@{punishment.get('target_user_id')}>\n"
                f"> Reason: {punishment.get('reason', 'No reason')}\n"
                f"> Issuer: <@{punishment.get('issuer_id')}>"
            )

            class EditCaseModal(discord.ui.Modal, title="Edit Case Reason"):
                def __init__(self, author: discord.Member, pid: str, current_reason: str):
                    super().__init__()
                    self.author = author
                    self.pid = pid
                    self.Reason = discord.ui.TextInput(label="Reason", default=current_reason)
                    self.add_item(self.Reason)

                async def on_submit(self, interaction: discord.Interaction):
                    if interaction.user.id != self.author.id and not await has_staff_role(interaction):
                        await interaction.response.send_message(f"{no} You don't have permission to edit this case.", ephemeral=True)
                        return
                    try:
                        await interaction.client.qdb["punishments"].update_one({"punishment_id": self.pid}, {"$set": {"reason": self.Reason.value}})
                    except Exception as e:
                        print(f"Error updating punishment reason: {e}")
                        await interaction.response.send_message(f"{no} Failed to update reason.", ephemeral=True)
                        return

                    # Update the log message embed in LOG_CHANNEL_ID if present
                    try:
                        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            async for message in log_channel.history(limit=500):
                                if message.embeds:
                                    for emb in message.embeds:
                                        footer_text = emb.footer.text if emb.footer else None
                                        if footer_text and self.pid in footer_text:
                                            try:
                                                edited = discord.Embed.from_dict(emb.to_dict())
                                                # Update reason in description
                                                if edited.description:
                                                    # Replace the reason line in description
                                                    lines = edited.description.split('\n')
                                                    new_lines = []
                                                    for line in lines:
                                                        if line.startswith('> Reason:'):
                                                            new_lines.append(f"> Reason: {self.Reason.value}")
                                                        else:
                                                            new_lines.append(line)
                                                    edited.description = '\n'.join(new_lines)
                                                await message.edit(embed=edited)
                                            except Exception as e:
                                                print(f"Error editing log embed reason: {e}")
                                            raise StopAsyncIteration
                    except StopAsyncIteration:
                        pass
                    except Exception as e:
                        print(f"Error updating log message: {e}")

                    try:
                        await interaction.response.send_message(f"{tick} Updated reason for `{self.pid}`.", ephemeral=True)
                    except Exception:
                        pass

            class DeleteCaseConfirm(discord.ui.View):
                def __init__(self, author: discord.Member, pid: str, target_id: int):
                    super().__init__(timeout=60)
                    self.author = author
                    self.pid = pid
                    self.target_id = target_id

                @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.red)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.author.id and not await has_staff_role(interaction):
                        await interaction.response.send_message(f"{no} You don't have permission to delete this case.", ephemeral=True)
                        return
                    try:
                        # Delete the punishment record
                        await interaction.client.qdb["punishments"].delete_one({"punishment_id": self.pid})
                        # Decrement modcases counter safely
                        try:
                            doc = await interaction.client.qdb["modcases"].find_one({"guild_id": interaction.guild.id, "user_id": self.target_id})
                            if doc:
                                newcount = max(0, int(doc.get("modcase_count", 0)) - 1)
                                await interaction.client.qdb["modcases"].update_one({"guild_id": interaction.guild.id, "user_id": self.target_id}, {"$set": {"modcase_count": newcount}})
                        except Exception:
                            pass

                        # Update the log message to indicate deletion
                        try:
                            log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
                            if log_channel:
                                async for message in log_channel.history(limit=500):
                                    if message.embeds:
                                        for emb in message.embeds:
                                            footer_text = emb.footer.text if emb.footer else None
                                            if footer_text and self.pid in footer_text:
                                                try:
                                                    edited = discord.Embed.from_dict(emb.to_dict())
                                                    edited.title = f"[DELETED] {edited.title}" if edited.title else "[DELETED] Case"
                                                    edited.color = discord.Color.dark_grey()
                                                    edited.add_field(name="Deleted By", value=f"<@{interaction.user.id}>", inline=False)
                                                    await message.edit(embed=edited)
                                                except Exception as e:
                                                    print(f"Error marking log message deleted: {e}")
                                                raise StopAsyncIteration
                        except StopAsyncIteration:
                            pass
                        except Exception as e:
                            print(f"Error updating log message on delete: {e}")

                        await interaction.response.send_message(f"{tick} Deleted punishment `{self.pid}`.", ephemeral=True)
                        self.stop()
                    except Exception as e:
                        print(f"Error deleting punishment: {e}")
                        await interaction.response.send_message(f"{no} Error deleting punishment.", ephemeral=True)

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_message(f"{no} Deletion cancelled.", ephemeral=True)
                    self.stop()

            # Present options to edit or delete
            view = discord.ui.View()

            async def edit_callback(interaction: discord.Interaction):
                # Open modal to edit reason
                modal = EditCaseModal(author=ctx.author, pid=punishment_id, current_reason=punishment.get("reason", ""))
                try:
                    await interaction.response.send_modal(modal)
                except Exception:
                    try:
                        await ctx.send(f"{no} Could not open modal.")
                    except Exception:
                        pass

            async def delete_callback(interaction: discord.Interaction):
                confirm = DeleteCaseConfirm(author=ctx.author, pid=punishment_id, target_id=punishment.get("target_user_id"))
                try:
                    await interaction.response.send_message("Are you sure you want to delete this case?", view=confirm, ephemeral=True)
                except Exception:
                    try:
                        await ctx.send("Could not open confirmation.")
                    except Exception:
                        pass

            # Buttons for interaction (use simple button wrappers)
            class EditButton(discord.ui.Button):
                def __init__(self):
                    super().__init__(label="Edit Reason", style=discord.ButtonStyle.blurple)

                async def callback(self, interaction: discord.Interaction):
                    await edit_callback(interaction)

            class DeleteButton(discord.ui.Button):
                def __init__(self):
                    super().__init__(label="Delete Case", style=discord.ButtonStyle.red)

                async def callback(self, interaction: discord.Interaction):
                    await delete_callback(interaction)

            view.add_item(EditButton())
            view.add_item(DeleteButton())

            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"Error in editcase command: {e}")
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="kick", aliases=["k"])
    @app_commands.describe(users="Users to kick (up to 5)", reason="Reason for the kick")
    @commands.check(has_kick_ban_role)
    async def kick_cmd(self, ctx: commands.Context, users: commands.Greedy[discord.User], *, reason: str = None):
        """Kick users"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("KICK_BAN_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to kick users.")
                return
            
            # Check rate limit: 15 kicks per hour
            is_allowed, remaining = self.check_punishment_limit(ctx.author.id, "kick", limit=15, hours=1)
            if not is_allowed:
                await ctx.send(f"{no} You've reached your kick limit (15 per hour). Try again later.")
                return
            
            # Limit to 5 users
            users = users[:5] if users else []
            if not users:
                await ctx.send(f"{no} Please specify at least one user to kick.")
                return
            
            # Parse reason for prefix commands (extract after ?r)
            final_reason = "No reason given"
            if reason:
                if "?r" in reason:
                    parts = reason.split("?r", 1)
                    final_reason = parts[1].strip() if len(parts) > 1 else "No reason given"
                elif reason.strip():
                    final_reason = reason.strip()
            
            results = []
            for target in users:
                try:
                    # Check whitelist
                    try:
                        target_member = await ctx.guild.fetch_member(target.id)
                        is_whitelisted = (
                            target_member.guild_permissions.administrator or
                            any(role.id == PUNISHMENT_WHITELIST_ROLE for role in target_member.roles)
                        )
                        if is_whitelisted:
                            results.append((target, False, "Whitelisted"))
                            continue
                    except discord.NotFound:
                        pass

                    punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    punishment_data = {
                        "punishment_id": punishment_id,
                        "guild_id": ctx.guild.id,
                        "target_user_id": target.id,
                        "punishment_type": "kick",
                        "reason": reason,
                        "issuer_id": ctx.author.    id,
                        "timestamp": datetime.now(),
                        "proofs": [],
                    }
                    await ctx.bot.qdb["punishments"].insert_one(punishment_data)
                    # Increment modcases quota counter for this guild/user
                    try:
                        await ctx.bot.qdb["modcases"].update_one(
                            {"guild_id": ctx.guild.id, "user_id": target.id},
                            {"$inc": {"modcase_count": 1}},
                            upsert=True,
                        )
                    except Exception as e:
                        print(f"Error updating quota for kick: {e}")
                    try:
                        target_member = await ctx.guild.fetch_member(target.id)
                        # DM before kicking
                        try:
                            target_user = await ctx.bot.fetch_user(target.id)
                            dm_embed = discord.Embed(
                                title=f"👢 You have been kicked from **{ctx.guild.name}**.",
                                description=f"> Moderator: <@{ctx.author.id}>\n> Reason: **{final_reason}**",
                                color=discord.Color.from_rgb(255, 0, 0),
                                timestamp=datetime.now()
                            )
                            dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            await target_user.send(embed=dm_embed)
                        except Exception:
                            pass

                        await target_member.kick(reason=reason)
                    except Exception:
                        pass

                    # Log to channel
                    try:
                        log_channel = ctx.bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            embed = discord.Embed(
                                color=discord.Color.from_rgb(54, 57, 63),
                                timestamp=datetime.now(),
                            )
                            embed.set_author(name=f"Punishment Issued", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            embed.description = (
                                f"**Punishment Type:** Kick\n\n"
                                f"> Target User: <@{target.id}>\n"
                                f"> Punished User ID: `{target.id}`\n"
                                f"> Reason: {final_reason}\n"
                                f"> Issuer: <@{ctx.author.id}>"
                            )
                            embed.set_footer(text=f"Punishment ID: {punishment_id}", icon_url=ctx.author.display_avatar)
                            await log_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error logging punishment: {e}")

                    results.append((target, True, punishment_id))
                    # Record the successful kick for rate limiting
                    self.add_punishment_record(ctx.author.id, "kick")
                except Exception as e:
                    results.append((target, False, str(e)))

            # Build summary embed (matching warn format)
            try:
                guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                ids_text = ", ".join([f"`{r[2]}`" for r in results if r[1]]) or "None"
                success_count = sum(1 for r in results if r[1])
                embed_color = discord.Color.from_rgb(102, 255, 0) if success_count > 0 else discord.Color.from_rgb(255, 0, 0)
                embed = discord.Embed(
                    description=(
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {final_reason}\n"
                        f"> {usr} Punishment ID(s): {ids_text}"
                    ),
                    color=embed_color,
                    timestamp=datetime.now(),
                )

                success_lines = []
                fail_lines = []
                for target, ok, punishment_id in results:
                    if ok:
                        success_lines.append(f"> {usr} <@{target.id}> (`{punishment_id}`)")
                    else:
                        fail_lines.append(f"{redx} <@{target.id}> — {punishment_id}")

                if success_lines:
                    embed.add_field(name=f"{greencheck} Kicked:", value="\n".join(success_lines), inline=False)
                if fail_lines:
                    embed.add_field(name="Failures:", value="\n".join(fail_lines), inline=False)

                embed.set_author(name="Kick Result", icon_url=ctx.bot.user.display_avatar.url if ctx.bot.user else None)
                embed.set_footer(text="All tasks completed", icon_url=guild_icon)

                # Create Attach Proofs view only if there were successful punishments
                punishment_ids = {r[2]: r[0].id for r in results if r[1]}
                if punishment_ids:
                    if len(punishment_ids) == 1:
                        single_id = list(punishment_ids.keys())[0]
                        view = AttachProofsView(single_id, self)
                    else:
                        view = AttachProofsSelectView(punishment_ids, self)
                    # Add guidance message
                    embed.add_field(name=f"{pen} Add Proofs", value=f"Click the button/dropdown below to start adding proofs to this case.", inline=False)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
                
                # Check for missing logging channels
                channel_warnings = await check_logging_channels(ctx, config)
                if channel_warnings:
                    await ctx.send(channel_warnings)
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="ban", aliases=["b"])
    @app_commands.describe(users="Users to ban (up to 5)", reason="Reason for the ban")
    @commands.check(has_kick_ban_role)
    async def ban_cmd(self, ctx: commands.Context, users: commands.Greedy[discord.User], *, reason: str = None):
        """Ban users"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("KICK_BAN_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to ban users.")
                return
            
            # Check rate limit: 15 bans per hour
            is_allowed, remaining = self.check_punishment_limit(ctx.author.id, "ban", limit=15, hours=1)
            if not is_allowed:
                await ctx.send(f"{no} You've reached your ban limit (15 per hour). Try again later.")
                return
            
            # Limit to 5 users
            users = users[:5] if users else []
            if not users:
                await ctx.send(f"{no} Please specify at least one user to ban.")
                return
            
            # Parse reason for prefix commands (extract after ?r)
            final_reason = "No reason given"
            if reason:
                if "?r" in reason:
                    parts = reason.split("?r", 1)
                    final_reason = parts[1].strip() if len(parts) > 1 else "No reason given"
                elif reason.strip():
                    final_reason = reason.strip()
            
            results = []
            for target in users:
                try:
                    try:
                        target_member = await ctx.guild.fetch_member(target.id)
                        is_whitelisted = (
                            target_member.guild_permissions.administrator or
                            any(role.id == PUNISHMENT_WHITELIST_ROLE for role in target_member.roles)
                        )
                        if is_whitelisted:
                            results.append((target, False, "Whitelisted"))
                            continue
                    except discord.NotFound:
                        pass

                    punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    punishment_data = {
                        "punishment_id": punishment_id,
                        "guild_id": ctx.guild.id,
                        "target_user_id": target.id,
                        "punishment_type": "ban",
                        "reason": final_reason,
                        "issuer_id": ctx.author.id,
                        "timestamp": datetime.now(),
                        "proofs": [],
                    }
                    await ctx.bot.qdb["punishments"].insert_one(punishment_data)
                    # Increment modcases quota counter for this guild/user
                    try:
                        await ctx.bot.qdb["modcases"].update_one(
                            {"guild_id": ctx.guild.id, "user_id": target.id},
                            {"$inc": {"modcase_count": 1}},
                            upsert=True,
                        )
                    except Exception as e:
                        print(f"Error updating quota for ban: {e}")
                    try:
                        # DM before banning
                        try:
                            target_user = await ctx.bot.fetch_user(target.id)
                            dm_embed = discord.Embed(
                                title=f"🔨 You have been banned from **{ctx.guild.name}**.",
                                description=f"> Moderator: <@{ctx.author.id}>\n> Reason: **{final_reason}**",
                                color=discord.Color.from_rgb(255, 0, 0),
                                timestamp=datetime.now()
                            )
                            dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            await target_user.send(embed=dm_embed)
                        except Exception:
                            pass

                        await ctx.guild.ban(discord.Object(target.id), reason=final_reason)
                    except Exception as e:
                        print(f"Error banning member: {e}")

                    # Log to channel
                    try:
                        log_channel = ctx.bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            embed = discord.Embed(
                                color=discord.Color.from_rgb(54, 57, 63),
                                timestamp=datetime.now(),
                            )
                            embed.set_author(name=f"Punishment Issued", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            embed.description = (
                                f"**Punishment Type:** Ban\n\n"
                                f"> Target User: <@{target.id}>\n"
                                f"> Punished User ID: `{target.id}`\n"
                                f"> Reason: {final_reason}\n"
                                f"> Issuer: <@{ctx.author.id}>"
                            )
                            embed.set_footer(text=f"Punishment ID: {punishment_id}", icon_url=ctx.author.display_avatar)
                            await log_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error logging punishment: {e}")

                    results.append((target, True, punishment_id))
                    # Record the successful ban for rate limiting
                    self.add_punishment_record(ctx.author.id, "ban")
                except Exception as e:
                    results.append((target, False, str(e)))

            # Build summary embed (matching warn format)
            try:
                guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                ids_text = ", ".join([f"`{r[2]}`" for r in results if r[1]]) or "None"
                success_count = sum(1 for r in results if r[1])
                embed_color = discord.Color.from_rgb(102, 255, 0) if success_count > 0 else discord.Color.from_rgb(255, 0, 0)
                embed = discord.Embed(
                    description=(
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {final_reason}\n"
                        f"> {usr} Punishment ID(s): {ids_text}"
                    ),
                    color=embed_color,
                    timestamp=datetime.now(),
                )

                success_lines = []
                fail_lines = []
                for target, ok, punishment_id in results:
                    if ok:
                        success_lines.append(f"> {usr} <@{target.id}> (`{punishment_id}`)")
                    else:
                        fail_lines.append(f"{redx} <@{target.id}> — {punishment_id}")

                if success_lines:
                    embed.add_field(name=f"{greencheck} Banned:", value="\n".join(success_lines), inline=False)
                if fail_lines:
                    embed.add_field(name="Failures:", value="\n".join(fail_lines), inline=False)

                embed.set_author(name="Ban Result", icon_url=ctx.bot.user.display_avatar.url if ctx.bot.user else None)
                embed.set_footer(text="All tasks completed", icon_url=guild_icon)

                # Create Attach Proofs view only if there were successful punishments
                punishment_ids = {r[2]: r[0].id for r in results if r[1]}
                if punishment_ids:
                    if len(punishment_ids) == 1:
                        single_id = list(punishment_ids.keys())[0]
                        view = AttachProofsView(single_id, self)
                    else:
                        view = AttachProofsSelectView(punishment_ids, self)
                    # Add guidance message
                    embed.add_field(name=f"{pen} Add Proofs", value=f"Click the button/dropdown below to start adding proofs to this case.", inline=False)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
                
                # Check for missing logging channels
                channel_warnings = await check_logging_channels(ctx, config)
                if channel_warnings:
                    await ctx.send(channel_warnings)
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="timeout", aliases=["t", "mute"])
    @app_commands.describe(users="Users to timeout (up to 5)", duration="Duration (e.g., 1h, 30m, 1d)", reason="Reason for the timeout")
    @commands.check(has_warn_mute_role)
    async def timeout_cmd(self, ctx: commands.Context, users: commands.Greedy[discord.User], duration: str, *, reason: str = None):
        """Timeout users"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("WARN_MUTE_BANREQUEST_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to timeout users.")
                return
            
            # Limit to 5 users
            users = users[:5] if users else []
            if not users:
                await ctx.send(f"{no} Please specify at least one user to timeout.")
                return
            
            # Parse reason for prefix commands (extract after ?r)
            final_reason = "No reason given"
            if reason:
                if "?r" in reason:
                    parts = reason.split("?r", 1)
                    final_reason = parts[1].strip() if len(parts) > 1 else "No reason given"
                elif reason.strip():
                    final_reason = reason.strip()

            # Parse duration once
            duration_str = duration.lower()
            duration_seconds = 0
            formatted_duration = ""
            if "h" in duration_str:
                hours = int(duration_str.replace("h", "").strip())
                duration_seconds = hours * 3600
                formatted_duration = f"{hours}h"
            elif "m" in duration_str:
                minutes = int(duration_str.replace("m", "").strip())
                duration_seconds = minutes * 60
                formatted_duration = f"{minutes}m"
            elif "d" in duration_str:
                days = int(duration_str.replace("d", "").strip())
                duration_seconds = days * 86400
                formatted_duration = f"{days}d"

            if duration_seconds <= 0:
                await ctx.send(f"{no} Invalid duration format. Use 1h, 30m, 1d, etc.")
                return

            results = []
            from datetime import timedelta

            for target in users:
                try:
                    # Check whitelist per-target
                    try:
                        target_member = await ctx.guild.fetch_member(target.id)
                        is_whitelisted = (
                            target_member.guild_permissions.administrator or
                            any(role.id == PUNISHMENT_WHITELIST_ROLE for role in target_member.roles)
                        )
                        if is_whitelisted:
                            results.append((target, False, "Whitelisted"))
                            continue
                    except discord.NotFound:
                        pass

                    punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    punishment_data = {
                        "punishment_id": punishment_id,
                        "guild_id": ctx.guild.id,
                        "target_user_id": target.id,
                        "punishment_type": "timeout",
                        "reason": final_reason,
                        "issuer_id": ctx.author.id,
                        "timestamp": datetime.now(),
                        "duration": formatted_duration,
                        "proofs": [],
                    }
                    await ctx.bot.qdb["punishments"].insert_one(punishment_data)
                    # Increment modcases quota counter for this guild/user
                    try:
                        await ctx.bot.qdb["modcases"].update_one(
                            {"guild_id": ctx.guild.id, "user_id": target.id},
                            {"$inc": {"modcase_count": 1}},
                            upsert=True,
                        )
                    except Exception as e:
                        print(f"Error updating quota for timeout: {e}")
                    try:
                        try:
                            target_user = await ctx.bot.fetch_user(target.id)
                            dm_embed = discord.Embed(
                                title=f"⏱️ You have been timed out in **{ctx.guild.name}**.",
                                description=f"> Moderator: <@{ctx.author.id}>\n> Reason: **{final_reason}**",
                                color=discord.Color.from_rgb(255, 0, 0),
                                timestamp=datetime.now()
                            )
                            dm_embed.set_footer(text="Please adhere to the server rules to avoid further action.", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            await target_user.send(embed=dm_embed)
                        except Exception:
                            pass

                        member = await ctx.guild.fetch_member(target.id)
                        await member.timeout(timedelta(seconds=duration_seconds), reason=final_reason)
                    except Exception as e:
                        print(f"Error applying timeout: {e}")

                    # Log to channel
                    try:
                        log_channel = ctx.bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            embed = discord.Embed(
                                color=discord.Color.from_rgb(54, 57, 63),
                                timestamp=datetime.now(),
                            )
                            embed.set_author(name=f"Punishment Issued", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            embed.description = (
                                f"**Punishment Type:** Timeout\n\n"
                                f"> Target User: <@{target.id}>\n"
                                f"> Punished User ID: `{target.id}`\n"
                                f"> Reason: {final_reason}\n"
                                f"> Duration: {formatted_duration}\n"
                                f"> Issuer: <@{ctx.author.id}>"
                            )
                            embed.set_footer(text=f"Punishment ID: {punishment_id}", icon_url=ctx.author.display_avatar)
                            await log_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error logging punishment: {e}")

                    results.append((target, True, punishment_id))
                except Exception as e:
                    results.append((target, False, str(e)))

            # Build summary embed (matching warn format)
            try:
                guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                ids_text = ", ".join([f"`{r[2]}`" for r in results if r[1]]) or "None"
                success_count = sum(1 for r in results if r[1])
                embed_color = discord.Color.from_rgb(102, 255, 0) if success_count > 0 else discord.Color.from_rgb(255, 0, 0)
                embed = discord.Embed(
                    description=(
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {final_reason}\n"
                        f"> {usr} Punishment ID(s): {ids_text}"
                    ),
                    color=embed_color,
                    timestamp=datetime.now(),
                )

                success_lines = []
                fail_lines = []
                for target, ok, punishment_id in results:
                    if ok:
                        success_lines.append(f"> {usr} <@{target.id}> (`{punishment_id}`)")
                    else:
                        fail_lines.append(f"{redx} <@{target.id}> — {punishment_id}")

                if success_lines:
                    embed.add_field(name=f"{greencheck} Timed out:", value="\n".join(success_lines), inline=False)
                if fail_lines:
                    embed.add_field(name="Failures:", value="\n".join(fail_lines), inline=False)

                embed.set_author(name="Timeout Result", icon_url=ctx.bot.user.display_avatar.url if ctx.bot.user else None)
                embed.set_footer(text="All tasks completed", icon_url=guild_icon)

                # Create Attach Proofs view only if there were successful punishments
                punishment_ids = {r[2]: r[0].id for r in results if r[1]}
                if punishment_ids:
                    if len(punishment_ids) == 1:
                        single_id = list(punishment_ids.keys())[0]
                        view = AttachProofsView(single_id, self)
                    else:
                        view = AttachProofsSelectView(punishment_ids, self)
                    # Add guidance message
                    embed.add_field(name=f"{pen} Add Proofs", value=f"Click the button/dropdown below to start adding proofs to this case.", inline=False)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
                
                # Check for missing logging channels
                channel_warnings = await check_logging_channels(ctx, config)
                if channel_warnings:
                    await ctx.send(channel_warnings)
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="unban", aliases=["ub"])
    @app_commands.describe(user="User to unban", reason="Reason for the unban")
    @commands.check(has_kick_ban_role)
    async def unban_cmd(self, ctx: commands.Context, user: discord.User, *, reason: str = None):
        """Unban a user"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("KICK_BAN_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to unban users.")
                return
            
            # Unban user
            try:
                await ctx.guild.unban(user, reason=reason)
            except Exception as e:
                print(f"Error unbanning member: {e}")
                await ctx.send(f"{no} Error unbanning user: {str(e)}")
                return

            # Log to channel
            try:
                log_channel = ctx.bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        color=discord.Color.from_rgb(54, 57, 63),
                        timestamp=datetime.now(),
                    )
                    embed.set_author(name=f"Punishment Issued", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                    embed.description = (
                        f"**Punishment Type:** Unban\n\n"
                        f"> Target User: <@{user.id}>\n"
                        f"> Punished User ID: `{user.id}`\n"
                        f"> Reason: {reason}\n"
                        f"> Issuer: <@{ctx.author.id}>"
                    )
                    embed.set_footer(text=f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", icon_url=ctx.author.display_avatar)
                    await log_channel.send(embed=embed)
            except Exception as e:
                print(f"Error logging unban: {e}")

            try:
                guild_icon = None
                if ctx.guild and ctx.guild.icon:
                    guild_icon = ctx.guild.icon.url
                success_embed = discord.Embed(
                    description=(
                        f"**{tick} Successfully unbanned <@{user.id}>.**\n\n"
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {reason}\n"
                    ),
                    color=discord.Color.from_rgb(102, 255, 0),
                    timestamp=datetime.now(),
                )
                success_embed.set_footer(text=f"Punished User ID : {user.id}", icon_url=guild_icon)
                await ctx.send(embed=success_embed)
            except Exception:
                msg = (
                    f"{tick} Successfully unbanned <@{user.id}>.\n\n"
                    f"> {modd} Moderator: <@{ctx.author.id}>\n"
                    f"> {reason_emoji} Reason: {reason}\n"
                )
                await ctx.send(msg)
            
            # Check for missing logging channels
            channel_warnings = await check_logging_channels(ctx, config)
            if channel_warnings:
                await ctx.send(channel_warnings)
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @commands.hybrid_command(name="banrequest", aliases=["br"])
    @app_commands.describe(users="Users to request ban for (up to 5)", reason="Reason for the ban request")
    @commands.check(has_warn_mute_role)
    async def banrequest_cmd(self, ctx: commands.Context, users: commands.Greedy[discord.User], *, reason: str = None):
        """Request a ban for users"""
        try:
            # Check config at start
            is_configured, error_msg = await check_moderation_config(ctx)
            if not is_configured:
                await ctx.send(error_msg)
                return
            
            config = await get_moderation_config(ctx.bot, ctx.guild.id)
            
            # Check if user has required role
            if not any(role.id == config.get("WARN_MUTE_BANREQUEST_ROLE") for role in ctx.author.roles):
                await ctx.send(f"{no} You don't have permission to request bans.")
                return
            
            # Limit to 5 users
            users = users[:5] if users else []
            if not users:
                await ctx.send(f"{no} Please specify at least one user to request a ban for.")
                return
            
            # Parse reason for prefix commands (extract after ?r)
            final_reason = "No reason given"
            if reason:
                if "?r" in reason:
                    parts = reason.split("?r", 1)
                    final_reason = parts[1].strip() if len(parts) > 1 else "No reason given"
                elif reason.strip():
                    final_reason = reason.strip()
            
            results = []
            ban_request_ids = {}  # {punishment_id: user_id}

            for target in users:
                try:
                    # Check if target user is whitelisted
                    try:
                        target_member = await ctx.guild.fetch_member(target.id)
                        is_whitelisted = (
                            target_member.guild_permissions.administrator or
                            any(role.id == PUNISHMENT_WHITELIST_ROLE for role in target_member.roles)
                        )
                        if is_whitelisted:
                            results.append((target, False, "*Staff!*"))
                            continue
                    except discord.NotFound:
                        # User not in guild, allow ban request
                        pass
                    
                    # Generate punishment ID
                    punishment_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    # Create punishment record with request_ban type
                    punishment_data = {
                        "punishment_id": punishment_id,
                        "guild_id": ctx.guild.id,
                        "target_user_id": target.id,
                        "punishment_type": "request_ban",
                        "reason": final_reason,
                        "issuer_id": ctx.author.id,
                        "timestamp": datetime.now(),
                        "proofs": [],
                        "approved": False,
                    }
                    await ctx.bot.qdb["punishments"].insert_one(punishment_data)
                    
                    # Increment modcases quota counter for ban request issuer
                    try:
                        await ctx.bot.qdb["modcases"].update_one(
                            {"guild_id": ctx.guild.id, "user_id": ctx.author.id},
                            {"$inc": {"modcase_count": 1}},
                            upsert=True,
                        )
                    except Exception:
                        pass

                    # Send ban request to BAN_REQUEST_CHANNEL_ID
                    try:
                        ban_request_channel = ctx.bot.get_channel(BAN_REQUEST_CHANNEL_ID)
                        if ban_request_channel:
                            ban_embed = discord.Embed(
                                color=discord.Color.orange(),
                                timestamp=datetime.now(),
                            )
                            ban_embed.set_author(name=f"Ban Request | {punishment_id}", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                            ban_embed.description = (
                                f"**Punishment Type:** Ban Request\n\n"
                                f"> Target User: <@{target.id}>\n"
                                f"> Punished User ID: `{target.id}`\n"
                                f"> Reason: {final_reason}\n"
                                f"> Requested by: <@{ctx.author.id}>"
                            )
                            ban_embed.set_footer(text=f"Punishment ID: {punishment_id}")
                            
                            view = BanRequestView(punishment_id, target.id, final_reason, ctx.author.id)
                            await ban_request_channel.send(embed=ban_embed, view=view)
                    except Exception as e:
                        print(f"Error sending ban request: {e}")
                        raise

                    results.append((target, True, punishment_id))
                    ban_request_ids[punishment_id] = target.id
                except Exception as e:
                    results.append((target, False, str(e)))

            # Build summary embed
            try:
                guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                ids_text = ", ".join([f"`{r[2]}`" for r in results if r[1]]) or "None"
                success_count = sum(1 for r in results if r[1])
                embed_color = discord.Color.from_rgb(102, 255, 0) if success_count > 0 else discord.Color.from_rgb(255, 0, 0)
                embed = discord.Embed(
                    description=(
                        f"> {modd} Moderator: <@{ctx.author.id}>\n"
                        f"> {reason_emoji} Reason: {final_reason}\n"
                        f"> {usr} Ban Request ID(s): {ids_text}"
                    ),
                    color=embed_color,
                    timestamp=datetime.now(),
                )

                success_lines = []
                fail_lines = []
                for target, ok, punishment_id in results:
                    if ok:
                        success_lines.append(f"> {usr} <@{target.id}> (`{punishment_id}`)")
                    else:
                        fail_lines.append(f"{redx} <@{target.id}> — {punishment_id}")

                if success_lines:
                    embed.add_field(name=f"{greencheck} Ban Requests Sent:", value="\n".join(success_lines), inline=False)
                if fail_lines:
                    embed.add_field(name="Failures:", value="\n".join(fail_lines), inline=False)

                embed.set_author(name="Ban Request Result", icon_url=ctx.bot.user.display_avatar.url if ctx.bot.user else None)
                embed.set_footer(text="All tasks completed", icon_url=guild_icon)

                # Create Attach Proofs view only if there were successful punishments
                punishment_ids = {r[2]: r[0].id for r in results if r[1]}
                if punishment_ids:
                    if len(punishment_ids) == 1:
                        single_id = list(punishment_ids.keys())[0]
                        view = AttachProofsView(single_id, self)
                    else:
                        view = AttachProofsSelectView(punishment_ids, self)
                    # Add guidance message
                    embed.add_field(name=f"{pen} Add Proofs", value=f"Click the button/dropdown below to start adding proofs to this case.", inline=False)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
                
                # Check for missing logging channels
                channel_warnings = await check_logging_channels(ctx, config)
                if channel_warnings:
                    await ctx.send(channel_warnings)
            except Exception as e:
                await ctx.send(f"{no} Completed with errors: {str(e)}")
        except Exception as e:
            await ctx.send(f"{no} Error: {str(e)}")

    @app_commands.command(
        name="punishmentpanel",
        description="Show the punishment panel for issuing punishments",
    )
    async def punishment_panel(self, interaction: discord.Interaction):
        """Show punishment panel embed with dropdown"""
        try:
            await interaction.response.defer()
            
            # Quick admin check - no database queries
            has_admin = interaction.user.guild_permissions.administrator

            if not has_admin:
                await interaction.followup.send(
                    f"{no} You need admin permissions to use this command.",
                    ephemeral=True,
                )
                return

            # Create embed (panel-style with author image, HS thumbnail and bottom banner)
            PANEL_AUTHOR_IMAGE = "https://media.discordapp.net/attachments/1428408793435471965/1441463021481365555/66e3717e777c4de77813b39804c2b828.png?ex=6935004d&is=6933aecd&hm=06c8a9ceb1f2f3d41743cf76ed3a9b951f39cc04e8a543ddf430c67fdbd6d794&=&format=webp&quality=lossless&width=960&height=960"
            PANEL_HS_THUMB = "https://media.discordapp.net/attachments/1428408793435471965/1441463021481365555/66e3717e777c4de77813b39804c2b828.png?ex=6935004d&is=6933aecd&hm=06c8a9ceb1f2f3d41743cf76ed3a9b951f39cc04e8a543ddf430c67fdbd6d794&=&format=webp&quality=lossless&width=960&height=960"
            PANEL_BOTTOM_BANNER = "https://cdn.discordapp.com/attachments/1279106678196801641/1446875068318879796/Your_paragraph_text.png?ex=693592e9&is=69344169&hm=7bb063bc0a9f02c8c065efc1d0c54a1d53d10e5e9fb612f13d31dfd16bade1cf&"

            embed = discord.Embed(
                description="**ACTION PANEL**\n\nThis is an interface which allows moderators to directly punish users instead of writing the command.\n\nAll punishments will go to <#1432451511266578452> automatically.\n\nJr. Mods can use the `Ban Request` option, and a ban request will be sent in <#1432451652408971335> for Moderators to approve.\n\nSelect the action you want to take on a member by using the dropdown below.",
                color=discord.Color.from_rgb(54, 57, 63),
            )
            # Author image (left) and HS emblem (right)
            embed.set_author(name="Havenn Studios", icon_url=PANEL_AUTHOR_IMAGE)
            embed.set_thumbnail(url=PANEL_HS_THUMB)
            # Bottom banner like the examples
            try:
                embed.set_image(url=PANEL_BOTTOM_BANNER)
            except Exception:
                pass

            try:
                view = PunishmentPanelView(self, interaction.user.id)
            except Exception as e:
                print(f"Error creating view: {e}")
                import traceback
                traceback.print_exc()
                await interaction.followup.send(
                    f"Error creating view: {str(e)}",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=False,
            )
        except Exception as e:
            print(f"Error in punishment_panel: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"Error: {str(e)}",
                    ephemeral=True,
                )
            except Exception:
                pass

    @app_commands.command(
        name="attachproofs",
        description="Attach proof images to a punishment",
    )
    @app_commands.describe(
        punishment_id="The punishment ID to attach proofs to",
    )
    async def attach_proofs(
        self,
        interaction: discord.Interaction,
        punishment_id: str,
    ):
        """Attach proof images to a punishment via file upload"""

        # Verify punishment exists
        punishment = await interaction.client.qdb["punishments"].find_one(
            {"punishment_id": punishment_id}
        )

        if not punishment:
            await interaction.response.send_message(
                f"{no} Punishment ID `{punishment_id}` not found.",
                ephemeral=True,
            )
            return

        # Only issuer can attach proofs
        if punishment["issuer_id"] != interaction.user.id:
            # Check if user is staff
            if not any(
                role.id in [WARN_MUTE_BANREQUEST_ROLE, KICK_BAN_ROLE]
                for role in interaction.user.roles
            ):
                await interaction.response.send_message(
                    f"{no} You can only attach proofs to your own punishments.",
                    ephemeral=True,
                )
                return

        await interaction.response.send_message(
            f"**Uploading proofs for punishment `{punishment_id}`...**\n\nPlease upload your proof image(s) in the next message.",
            ephemeral=True,
        )

        def check(msg):
            return (
                msg.author == interaction.user
                and msg.channel == interaction.channel
                and len(msg.attachments) > 0
            )

        try:
            proof_message = await interaction.client.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            await interaction.followup.send(
                f"{no} Proof upload timed out (5 minutes).",
                ephemeral=True,
            )
            return

        if not proof_message.attachments:
            await interaction.followup.send(
                f"{no} No attachments found in your message.",
                ephemeral=True,
            )
            return

        # We'll attach proofs directly to the logged message below; no separate storage upload.
        proofs_to_store = []

        # Update log message with proofs: send a new message to the log channel that contains
        # the embed + attachments (so Discord displays the images under the embed), then
        # update the original log message to link to the new message.
        try:
            log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                found = False

                # Read attachment bytes so we can both upload to the log and show an ephemeral preview
                attachment_blobs = []
                for att in proof_message.attachments:
                    try:
                        data = await att.read()
                        attachment_blobs.append((att.filename, data))
                    except Exception as ex:
                        print(f"Failed to prepare attachment {att.filename} for log upload: {ex}")

                async for message in log_channel.history(limit=500):
                    if message.embeds:
                        for embed in message.embeds:
                            # Check if punishment ID is in footer or title
                            footer_text = embed.footer.text if embed.footer else None
                            if footer_text and punishment_id in footer_text:
                                # Found the original log message
                                # Create a copy of the embed so we can send it with attachments
                                try:
                                    new_embed = discord.Embed.from_dict(embed.to_dict())
                                except Exception:
                                    # Fallback to copying fields manually
                                    new_embed = embed

                                # Reply to the original log message with the proof files only (no embed)
                                try:
                                    files_for_log = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]

                                    if files_for_log:
                                        new_msg = await message.reply(files=files_for_log)
                                    else:
                                        new_msg = await message.reply(content=f"Proofs for punishment `{punishment_id}`")

                                    # Collect uploaded attachment URLs from the message we just sent
                                    uploaded_urls = [a.url for a in new_msg.attachments]

                                    # Use these uploaded URLs as the proofs to store
                                    proofs_to_store = uploaded_urls

                                    # Update the punishment record with the uploaded URLs
                                    await interaction.client.qdb["punishments"].update_one(
                                        {"punishment_id": punishment_id},
                                        {"$set": {"proofs": uploaded_urls}},
                                    )

                                    # Edit the original log message to link to the reply (so staff can jump to images)
                                    try:
                                        orig_edited = discord.Embed.from_dict(embed.to_dict())
                                    except Exception:
                                        orig_edited = embed
                                    orig_edited.add_field(name="Attached Proofs", value=f"[View proofs here]({new_msg.jump_url})", inline=False)
                                    await message.edit(embed=orig_edited)

                                except Exception as e:
                                    print(f"Error replying with attachments to log message: {e}")

                                found = True
                                break
                    if found:
                        break
        except Exception as e:
            print(f"Error updating log message: {e}")
            import traceback
            traceback.print_exc()

        # Send ephemeral preview of the uploaded images back to the user
        try:
            if attachment_blobs:
                ephemeral_files = [discord.File(io.BytesIO(data), filename=fn) for fn, data in attachment_blobs]
                await interaction.followup.send(f"{tick} Here is a preview of the image(s) you uploaded for `{punishment_id}`:", files=ephemeral_files, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"{tick} {len(proofs_to_store)} proof image(s) attached successfully!",
                    ephemeral=True,
                )
        except Exception:
            try:
                await interaction.followup.send(
                    f"{tick} {len(proofs_to_store)} proof image(s) attached successfully!",
                    ephemeral=True,
                )
            except Exception:
                pass

        # Delete the user's proof message to keep chat clean
        try:
            await proof_message.delete()
        except:
            pass

    @commands.hybrid_command(name="case", aliases=["cases"])
    async def case_hybrid(self, ctx: commands.Context, user_or_id: Optional[str] = None):
        """View modcases: single case by ID, user's cases, or all server cases"""
        try:
            if isinstance(ctx, discord.Interaction):
                # Slash command context
                await ctx.response.defer()
                send_func = ctx.followup.send
            else:
                # Prefix command context
                send_func = ctx.send

            if not user_or_id:
                # No argument: show all server cases with pagination
                query = {"guild_id": ctx.guild.id}
                cases = list(await ctx.bot.qdb["punishments"].find(query).sort("timestamp", -1).to_list(None))
                case_count = len(cases)
                title = f"{ctx.guild.name} cases ({case_count})"

                if not cases:
                    embed = discord.Embed(
                        description="No modcases found.",
                        color=discord.Color.from_rgb(54, 57, 63),
                    )
                    embed.set_author(name=title, icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                    await send_func(embed=embed)
                    return

                # Paginate: 10 cases per page
                cases_per_page = 10
                total_pages = (len(cases) + cases_per_page - 1) // cases_per_page
                current_page = 0

                async def build_page_all(page_num):
                    start = page_num * cases_per_page
                    end = start + cases_per_page
                    page_cases = cases[start:end]

                    case_lines = []
                    for case in page_cases:
                        case_type = case['punishment_type'].upper()
                        time_delta = discord.utils.format_dt(case['timestamp'], style='R')
                        case_line = f"{greencheck} `{case['punishment_id']}` **[{case_type}]** {time_delta}"
                        case_lines.append(case_line)

                    description = "\n".join(case_lines)
                    embed = discord.Embed(
                        description=description,
                        color=discord.Color.from_rgb(54, 57, 63),
                    )
                    embed.set_author(name=title, icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
                    embed.set_footer(text=f"Page: {page_num + 1}/{total_pages}")
                    return embed

                # Send initial message with pagination controls
                msg = await send_func(embed=await build_page_all(current_page))
                await msg.add_reaction("◀")
                await msg.add_reaction("▶")
                await msg.add_reaction("❌")

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["◀", "▶", "❌"] and reaction.message.id == msg.id

                while True:
                    try:
                        reaction, user = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
                        await msg.remove_reaction(reaction, user)

                        if str(reaction.emoji) == "◀":
                            current_page = max(0, current_page - 1)
                        elif str(reaction.emoji) == "▶":
                            current_page = min(total_pages - 1, current_page + 1)
                        elif str(reaction.emoji) == "❌":
                            await msg.clear_reactions()
                            break

                        await msg.edit(embed=await build_page_all(current_page))
                    except TimeoutError:
                        await msg.clear_reactions()
                        break
                return

            # Try to parse as user mention or user ID
            user = None
            try:
                # Try to convert to user
                user = await commands.UserConverter().convert(ctx, user_or_id)
            except Exception:
                pass

            if user:
                # Query modcases for this user
                modcases = list(await ctx.bot.qdb["punishments"].find(
                    {"target_user_id": user.id, "guild_id": ctx.guild.id}
                ).sort("timestamp", -1).to_list(None))
                user_case_count = len(modcases)

                if not modcases:
                    embed = discord.Embed(
                        description="No modcases found.",
                        color=discord.Color.from_rgb(54, 57, 63),
                    )
                    embed.set_author(name=f"{user.display_name} cases ({user_case_count})", icon_url=user.display_avatar)
                    await send_func(embed=embed, ephemeral=True)
                    return

                # Paginate: 10 cases per page
                cases_per_page = 10
                total_pages = (len(modcases) + cases_per_page - 1) // cases_per_page
                current_page = 0

                async def build_page_user(page_num):
                    start = page_num * cases_per_page
                    end = start + cases_per_page
                    page_cases = modcases[start:end]

                    case_lines = []
                    for case in page_cases:
                        case_type = case['punishment_type'].upper()
                        time_delta = discord.utils.format_dt(case['timestamp'], style='R')
                        case_line = f"{greencheck} `{case['punishment_id']}` **[{case_type}]** {time_delta}"
                        case_lines.append(case_line)

                    description = "\n".join(case_lines)
                    embed = discord.Embed(
                        description=description,
                        color=discord.Color.from_rgb(54, 57, 63),
                    )
                    embed.set_author(name=f"{user.display_name} cases ({user_case_count})", icon_url=user.display_avatar)
                    embed.set_footer(text=f"Page: {page_num + 1}/{total_pages}")
                    return embed

                # Send initial message with pagination controls
                msg = await send_func(embed=await build_page_user(current_page))
                await msg.add_reaction("◀")
                await msg.add_reaction("▶")
                await msg.add_reaction("❌")

                def check(reaction, user_):
                    return user_ == ctx.author and str(reaction.emoji) in ["◀", "▶", "❌"] and reaction.message.id == msg.id

                while True:
                    try:
                        reaction, user_ = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
                        await msg.remove_reaction(reaction, user_)

                        if str(reaction.emoji) == "◀":
                            current_page = max(0, current_page - 1)
                        elif str(reaction.emoji) == "▶":
                            current_page = min(total_pages - 1, current_page + 1)
                        elif str(reaction.emoji) == "❌":
                            await msg.clear_reactions()
                            break

                        await msg.edit(embed=await build_page_user(current_page))
                    except TimeoutError:
                        await msg.clear_reactions()
                        break
            else:
                # Try to find case by ID
                case = await ctx.bot.qdb["punishments"].find_one(
                    {"punishment_id": user_or_id.upper(), "guild_id": ctx.guild.id}
                )

                if not case:
                    await send_func(f"{no} User or case ID `{user_or_id}` not found.", ephemeral=True)
                    return

                # Build embed for single case
                embed = discord.Embed(
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=case['timestamp'],
                )
                embed.set_author(
                    name=f"Punishment Issued",
                    icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
                )
                
                duration_text = f"\n> Duration: {case.get('duration', '')}" if case.get('punishment_type') == 'timeout' and case.get('duration') else ""
                embed.description = (
                    f"**Punishment Type:** {case['punishment_type'].title()}\n\n"
                    f"> Target User: <@{case['target_user_id']}>\n"
                    f"> Punished User ID: `{case['target_user_id']}`\n"
                    f"> Reason: {case['reason']}"
                    f"{duration_text}\n"
                    f"> Issuer: <@{case['issuer_id']}>"
                )
                
                if case.get('proofs'):
                    proofs_text = "\n".join([f"[Proof {i+1}]({url})" for i, url in enumerate(case['proofs'])])
                    embed.description += f"\n\n> Attached Proofs: {proofs_text}"
                
                embed.set_footer(text=f"Punishment ID: {case['punishment_id']}", icon_url=ctx.author.display_avatar)

                await send_func(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in case command: {e}")
            if isinstance(ctx, discord.Interaction):
                await ctx.followup.send(f"{no} Error: {str(e)}", ephemeral=True)
            else:
                await ctx.send(f"{no} Error: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="modcases", aliases=["mymodcases", "mycases", "mc"])
    async def modcases_hybrid(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """View modcases you have issued or check another user's cases"""
        try:
            # If user is provided, check that user's cases instead of the author's
            target_user = user if user else ctx.author
            
            # Query modcases issued by the target user
            my_cases = list(await ctx.bot.qdb["punishments"].find(
                {"issuer_id": target_user.id, "guild_id": ctx.guild.id}
            ).sort("timestamp", -1).to_list(None))
            my_case_count = len(my_cases)

            if not my_cases:
                embed = discord.Embed(
                    description="No modcases found.",
                    color=discord.Color.from_rgb(54, 57, 63),
                )
                embed.set_author(name=f"{target_user.display_name} modcases ({my_case_count})", icon_url=target_user.display_avatar)
                await ctx.send(embed=embed)
                return

            # Paginate: 10 cases per page
            cases_per_page = 10
            total_pages = (len(my_cases) + cases_per_page - 1) // cases_per_page
            current_page = 0

            async def build_page(page_num):
                start = page_num * cases_per_page
                end = start + cases_per_page
                page_cases = my_cases[start:end]

                case_lines = []
                for case in page_cases:
                    case_type = case['punishment_type'].upper()
                    time_delta = discord.utils.format_dt(case['timestamp'], style='R')
                    case_line = f"{greencheck} `{case['punishment_id']}` **[{case_type}]** {time_delta}"
                    case_lines.append(case_line)

                description = "\n".join(case_lines)
                embed = discord.Embed(
                    description=description,
                    color=discord.Color.from_rgb(54, 57, 63),
                )
                embed.set_author(name=f"{target_user.display_name} modcases ({my_case_count})", icon_url=target_user.display_avatar)
                embed.set_footer(text=f"Page: {page_num + 1}/{total_pages}")
                return embed

            # Send initial message with pagination controls
            msg = await ctx.send(embed=await build_page(current_page))
            await msg.add_reaction("◀")
            await msg.add_reaction("▶")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀", "▶", "❌"] and reaction.message.id == msg.id

            while True:
                try:
                    reaction, user = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    await msg.remove_reaction(reaction, user)

                    if str(reaction.emoji) == "◀":
                        current_page = max(0, current_page - 1)
                    elif str(reaction.emoji) == "▶":
                        current_page = min(total_pages - 1, current_page + 1)
                    elif str(reaction.emoji) == "❌":
                        await msg.clear_reactions()
                        break

                    await msg.edit(embed=await build_page(current_page))
                except TimeoutError:
                    await msg.clear_reactions()
                    break
        except Exception as e:
            print(f"Error in modcases hybrid command: {e}")
            await ctx.send(f"{no} Error: {str(e)}")


async def setup(client: commands.Bot):
    await client.add_cog(PunishmentPanel(client))
