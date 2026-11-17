import re
import discord


EMOJI_ROLE_FORMAT = "React with {emoji} to this message to receive the {role} role."
EMOJI_ROLE_MATCH = re.compile(fr"^{EMOJI_ROLE_FORMAT.format(emoji=r"(.+)", role=r"<@&(\d+)>")}")


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

    # region Emoji Role

    # (Channel ID, Message ID) -> (Emoji, Role ID)
    _role_dict: dict[tuple[int, int], tuple[str, discord.Role]] = {}

    async def fetch_emoji_role(self, guild_id: int, channel_id: int, message_id: int) -> None | tuple[str, discord.Role]:
        if (channel_id, message_id) in self._role_dict:
            return self._role_dict[(channel_id, message_id)]

        message = await self.get_bot_message(guild_id, channel_id, message_id)

        if message is None or (match := EMOJI_ROLE_MATCH.match(message.content)) is None:
            return None

        emoji = match.group(1)
        role_id = int(match.group(2))
        role = message.guild.get_role(role_id)

        self._role_dict[(channel_id, message_id)] = (emoji, role)
        return emoji, role

    async def register_emoji_role(self, channel: discord.abc.Messageable, emoji: str, role: discord.Role, desc: str | None = None):
        content = EMOJI_ROLE_FORMAT.format(emoji=emoji, role=role.mention)
        if desc is not None:
            content += "\n\n" + desc

        message: discord.Message | None = None
        try:
            message = await channel.send(content=content)
            await message.add_reaction(emoji)
        except discord.HTTPException as e:
            if message:
                await message.delete()
            raise e

        self._role_dict[(message.channel.id, message.id)] = (emoji, role)

    # endregion

    # region Cache

    # Guild ID -> Guild
    _guild_cache: dict[int, discord.Guild | None] = {}

    def get_guild(self, guild_id: int, /) -> discord.Guild | None:
        if guild_id not in self._guild_cache:
            self._guild_cache[guild_id] = super().get_guild(guild_id)

        return self._guild_cache.get(guild_id)

    # (Guild ID, User ID) -> Member
    _member_cache: dict[tuple[int, int], discord.Member | None] = {}

    def get_guild_member(self, guild_id: int, member_id: int, /) -> discord.Member | None:
        if member_id == self.user.id:
            return None

        if (guild_id, member_id) not in self._member_cache:
            if (guild := self.get_guild(guild_id)) is not None:
                self._member_cache[(guild_id, member_id)] = guild.get_member(member_id)

        return self._member_cache.get((guild_id, member_id))

    # (Guild ID, Channel ID) -> Channel
    _channel_cache: dict[tuple[int, int], discord.abc.Messageable | None] = {}

    def get_guild_channel(self, guild_id: int, channel_id: int, /) -> discord.abc.Messageable | None:
        if (guild_id, channel_id) not in self._channel_cache:
            if (guild := self.get_guild(guild_id)) is not None:
                self._channel_cache[(guild_id, channel_id)] = guild.get_channel(channel_id)

        return self._channel_cache.get((guild_id, channel_id))

    # (Guild ID, Channel ID, Message ID) -> Message
    _message_cache: dict[tuple[int, int, int], discord.Message | None] = {}

    async def get_bot_message(self, guild_id: int, channel_id: int, message_id: int, /) -> discord.Message | None:
        if (guild_id, channel_id, message_id) not in self._message_cache:
            if (channel := self.get_guild_channel(guild_id, channel_id)) is not None:
                if (message := await channel.fetch_message(message_id)) is not None and message.author == self.user:
                    self._message_cache[(guild_id, channel_id, message_id)] = message

        return self._message_cache.get((guild_id, channel_id, message_id))

    # endregion

    # region Events

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        guild_id, channel_id, message_id = payload.guild_id, payload.channel_id, payload.message_id
        if (guild_id, channel_id, message_id) not in self._message_cache:
            return

        channel = self.get_guild_channel(guild_id, channel_id)
        self._message_cache[(guild_id, channel_id, message_id)] = await channel.fetch_message(message_id)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        guild_id, channel_id, message_id = payload.guild_id, payload.channel_id, payload.message_id
        self._remove_message_cache(guild_id, channel_id, message_id)

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        guild_id, channel_id = payload.guild_id, payload.channel_id
        for message_id in payload.message_ids:
            self._remove_message_cache(guild_id, channel_id, message_id)

    async def on_raw_poll_vote_add(self, payload: discord.RawPollVoteActionEvent):
        member = self.get_guild_member(payload.guild_id, payload.user_id)
        if not member or member.bot:
            return

        message = await self.get_bot_message(payload.guild_id, payload.channel_id, payload.message_id)
        if not message or message.poll is None:
            return

        answer = message.poll.get_answer(payload.answer_id)
        if not answer:
            return

        print(f"{member.name} voted for '{answer.text}' in poll: '{message.poll.question}'")

    async def on_raw_poll_vote_remove(self, payload: discord.RawPollVoteActionEvent):
        member = self.get_guild_member(payload.guild_id, payload.user_id)
        if not member or member.bot:
            return

        message = await self.get_bot_message(payload.guild_id, payload.channel_id, payload.message_id)
        if not message or message.poll is None:
            return

        answer = message.poll.get_answer(payload.answer_id)
        if not answer:
            return

        print(f"{member.name} removed their vote for '{answer.text}' in poll: '{message.poll.question}'")

    # endregion

    def _remove_message_cache(self, guild_id: int, channel_id: int, message_id: int):
        self._message_cache.pop((guild_id, channel_id, message_id), None)
        self._role_dict.pop((channel_id, message_id), None)
