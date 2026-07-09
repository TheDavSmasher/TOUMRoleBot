import discord


class MongyClient(discord.Client):

    # (Channel ID, Message ID) -> (Emoji, Role ID)
    _role_dict: dict[tuple[int, int], tuple[str, discord.Role]] = {}

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.reactions = True
        intents.message_content = True
        intents.guild_scheduled_events = True
        intents.guild_polls = True

        mentions = discord.AllowedMentions(everyone=True)

        super().__init__(intents=intents, allowed_mentions=mentions)

    async def fetch_emoji_role(self, guild: discord.Guild, channel_id: int, message_id: int) -> None | tuple[str, discord.Role]:
        if (channel_id, message_id) in self._role_dict:
            return self._role_dict[(channel_id, message_id)]

        channel = guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)

        # TODO: format message and REGEX
        if message.content.startswith('<@!'):
            return None
        return None
