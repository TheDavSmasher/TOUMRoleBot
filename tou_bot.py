import os
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
