import re
import discord

from discord import app_commands


CUSTOM_EMOJI_REGEX = re.compile(r"^<a?:[a-zA-Z0-9_]{2,32}:[0-9]{17,22}>$")


class EmojiTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> discord.PartialEmoji | str:
        value = value.strip()

        if CUSTOM_EMOJI_REGEX.match(value):
            return discord.PartialEmoji.from_str(value)

        if len(value) <= 7 and not value.isascii():
            return value

        raise app_commands.AppCommandError("Please provide a valid standard or custom emoji.")
