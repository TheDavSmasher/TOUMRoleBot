import os
from datetime import timedelta

import discord
from discord import app_commands

from bot_client import MongyClient
from role_types import AlignData
from tou_bot_layout import MongyLayout, filtered, reload_config, get_role_list, RoleLayout


client = MongyClient()
tree = app_commands.CommandTree(client)


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
    try:
        await interaction.response.defer(
            ephemeral=True
        )
        config_byes = await config_file.read()
        reload_config(config_byes)
        await interaction.followup.send(
            "Active roles updated.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while loading new file: {e}",
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


@tree.command(name="session_poll", description="Create a poll for session attendance.")
@app_commands.describe(ping="Ping @everyone")
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

    await interaction.response.send_message(
        content="@everyone" if ping else None,
        poll=poll
    )


@client.event
async def on_raw_poll_vote_add(payload: discord.RawPollVoteActionEvent):
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)
    if not message:
        return

    answer = message.poll.get_answer(payload.answer_id)
    if not answer:
        return

    print(f"{member.name} voted for '{answer.text}' in poll: '{answer.poll.question}'")


@client.event
async def on_raw_poll_vote_remove(payload: discord.RawPollVoteActionEvent):
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)
    if not message:
        return

    answer = message.poll.get_answer(payload.answer_id)
    if not answer:
        return

    print(f"{member.name} removed their vote for '{answer.text}' in poll: '{answer.poll.question}'")


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    emoji_role = await client.fetch_emoji_role(guild, payload.channel_id, payload.message_id)
    if not emoji_role:
        return

    emoji, role = emoji_role
    if str(payload.emoji) != emoji:
        return

    await member.add_roles(role)


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    emoji_role = await client.fetch_emoji_role(guild, payload.channel_id, payload.message_id)
    if not emoji_role:
        return

    emoji, role = emoji_role
    if str(payload.emoji) != emoji:
        return

    await member.remove_roles(role)


@client.event
async def on_ready():
    await tree.sync()


if __name__ == "__main__":
    token = os.getenv('TOKEN')
    client.run(token)
