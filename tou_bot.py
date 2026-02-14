import os
import discord
from discord import app_commands

from tou_bot_layout import MongyLayout, filtered, reload_config

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
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
        await interaction.response.defer()
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


@client.event
async def on_ready():
    await tree.sync()

token = os.getenv('TOKEN')


if __name__ == "__main__":
    client.run(token)
