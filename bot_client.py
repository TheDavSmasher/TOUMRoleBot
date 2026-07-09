import discord


class MongyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.reactions = True
        intents.message_content = True
        intents.guild_scheduled_events = True
        intents.guild_polls = True

        mentions = discord.AllowedMentions(everyone=True)

        super().__init__(intents=intents, allowed_mentions=mentions)
