import os
from datetime import timedelta

import discord
from discord import app_commands

from bot_client import MongyClient
from emoji_transformer import EmojiTransformer
from role_types import AlignData
from tou_bot_layout import MongyLayout, filtered, reload_config, get_role_list, RoleLayout


MONGY_REGULAR_ROLE_ID = 1572303236080341173

SERVER_ROLES_CHANNEL_ID = 1524624589232017569
SESSION_PLANNING_CHANNEL_ID = 1470829176066937057

TEST_CHANNEL_ID = 1572055173864362145


client = MongyClient()
tree = app_commands.CommandTree(client)


# region Commands

# region Role Commands

@tree.command(name="active_roles", description="View the currently active roles.")
async def active_roles(interaction: discord.Interaction):
    filtered(True)
    await interaction.response.send_message(
        view=MongyLayout(),
        ephemeral=True
    )


@tree.command(name="all_roles", description="View all roles in the mod.")
async def all_roles(interaction: discord.Interaction):
    filtered(False)
    await interaction.response.send_message(
        view=MongyLayout(),
        ephemeral=True
    )


@tree.command(name="update_roles", description="Update the roles marked as active.")
@app_commands.describe(config_file="Config file")
async def update_roles(interaction: discord.Interaction, config_file: discord.Attachment):
    await interaction.response.defer(
        ephemeral=True
    )
    config_byes = await config_file.read()
    reload_config(config_byes)
    await interaction.followup.send(
        "Active roles updated.",
        ephemeral=True
    )


@update_roles.error
async def update_roles_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.followup.send(
        f"An error occurred while loading new file: {error}",
        ephemeral=True
    )


async def find_role_autocomplete(_: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    role_list = [role for role in get_role_list() if current.lower() in role[0].lower()]
    return [app_commands.Choice(name=name, value=f"{name}:{align}") for name, align in sorted(role_list)[:25]]


@tree.command(name="find_role", description="Find a role by its name.")
@app_commands.autocomplete(role=find_role_autocomplete)
async def find_role(interaction: discord.Interaction, role: str):
    name, align = role.split(':')
    await interaction.response.send_message(
        view=RoleLayout(AlignData.from_str(align), name).load(),
        ephemeral=True
    )

# endregion


@tree.command(name="session_poll", description="Create a poll for session attendance.")
@app_commands.describe(ping="Ping @Mongy Regular")
async def host_session_poll(interaction: discord.Interaction, ping: bool):
    poll = discord.Poll(
        question="Days for Session",
        duration=timedelta(days=3),
        multiple=True
    )

    poll.add_answer(text="Monday")
    poll.add_answer(text="Tuesday")
    poll.add_answer(text="Wednesday")
    poll.add_answer(text="Thursday")
    poll.add_answer(text="Friday")
    poll.add_answer(text="Saturday")
    poll.add_answer(text="Unsure")
    poll.add_answer(text="Not this week")

    channel = client.get_guild_channel(interaction.guild_id, SESSION_PLANNING_CHANNEL_ID)

    role = None
    if ping:
        role = interaction.guild.get_role(MONGY_REGULAR_ROLE_ID)

    message = await channel.send(
        content=role.mention if role else None,
        poll=poll,
        allowed_mentions=discord.AllowedMentions(roles=True)
    )

    await client.track_poll(message, role)


@tree.command(name="register_react_role", description="Register an message with an emoji reaction to give out a role in the server.")
@app_commands.describe(role="The role to give to the user.", react_emoji="The emoji the message will expect in a reaction.", desc="Describe what the role does.")
async def register_react_role(
    interaction: discord.Interaction,
    role: discord.Role,
    react_emoji: app_commands.Transform[discord.PartialEmoji | str, EmojiTransformer],
    desc: str | None = None
):
    channel = client.get_guild_channel(interaction.guild_id, SERVER_ROLES_CHANNEL_ID)

    await client.register_react_role(channel, str(react_emoji), role, desc)

    await client.info(interaction.guild_id, f"Registered emoji {react_emoji} and role {role.mention} successfully")


@register_react_role.error
async def register_react_role_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await client.error(interaction.guild_id, f"An error occurred while registering an emoji role: {error}")

# endregion


# region Client Events

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    member = client.get_guild_member(payload.guild_id, payload.user_id)
    if not member:
        return

    react_role = await client.fetch_react_role(payload.guild_id, payload.channel_id, payload.message_id)
    if not react_role:
        return

    react_emoji, role = react_role
    if str(payload.emoji) != react_emoji:
        return

    await member.add_roles(role)

    await client.info(payload.guild_id, f"Added {role.mention} role to {member.mention}.")


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    member = client.get_guild_member(payload.guild_id, payload.user_id)
    if not member:
        return

    react_role = await client.fetch_react_role(payload.guild_id, payload.channel_id, payload.message_id)
    if not react_role:
        return

    react_emoji, role = react_role
    if str(payload.emoji) != react_emoji:
        return

    await member.remove_roles(role)

    await client.info(payload.guild_id, f"Removed {role.mention} role from {member.mention}.")


@client.event
async def on_ready():
    await tree.sync()

# endregion


if __name__ == "__main__":
    token = os.getenv('TOKEN')
    client.run(token)
