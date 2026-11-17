import re
import discord


REACT_ROLE_FORMAT = "React with {emoji} to this message to receive the {role} role."
REACT_ROLE_MATCH = re.compile(fr"^{REACT_ROLE_FORMAT.format(emoji=r"(.+)", role=r"<@&(\d+)>")}")

LOG_MESSAGE_MATCH = re.compile(r"\[(?:INFO|ERROR)]\s+.+")

BOT_LOG_CHANNEL_ID = 1571966492600180876


async def _get_poll_votes(poll: discord.Poll, role: discord.Role | None) -> set[int]:
    return set([user.id
                for answer in poll.answers
                async for user in answer.voters()
                if role is None or role in user.roles])


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

    # region React Role

    # (Channel ID, Message ID) -> (React Emoji, Role)
    _react_role_dict: dict[tuple[int, int], tuple[str, discord.Role]] = {}

    async def fetch_react_role(self, guild_id: int, channel_id: int, message_id: int) -> None | tuple[str, discord.Role]:
        if (channel_id, message_id) in self._react_role_dict:
            return self._react_role_dict[(channel_id, message_id)]

        message = await self.get_bot_message(guild_id, channel_id, message_id)

        if message is None or (match := REACT_ROLE_MATCH.match(message.content)) is None:
            return None

        self._remove_message_cache(guild_id, channel_id, message_id)

        react_emoji = match.group(1)
        role_id = int(match.group(2))
        role = message.guild.get_role(role_id)

        self._react_role_dict[(channel_id, message_id)] = (react_emoji, role)
        return react_emoji, role

    async def register_react_role(self, channel: discord.abc.Messageable, emoji: str, role: discord.Role, desc: str | None = None):
        content = REACT_ROLE_FORMAT.format(emoji=emoji, role=role.mention)
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

        self._react_role_dict[(message.channel.id, message.id)] = (emoji, role)

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

    def get_guild_member(self, guild_id: int, user_id: int, /) -> discord.Member | None:
        if user_id == self.user.id:
            return None

        if (guild_id, user_id) not in self._member_cache:
            if (guild := self.get_guild(guild_id)) is not None:
                member = guild.get_member(user_id)
                if member is not None and not member.bot:
                    self._member_cache[(guild_id, user_id)] = member

        return self._member_cache.get((guild_id, user_id))

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
                message = await channel.fetch_message(message_id)
                if message is not None and message.author == self.user and not LOG_MESSAGE_MATCH.match(message.content):
                    self._message_cache[(guild_id, channel_id, message_id)] = message

        return self._message_cache.get((guild_id, channel_id, message_id))

    def cache_sent_message(self, message: discord.Message):
        self._message_cache[(message.guild.id, message.channel.id, message.id)] = message

    # endregion

    # region Poll Tracking

    PollVotes = tuple[set[int], discord.Role | None]

    # (Guild ID, Channel ID, Message ID) -> (User IDs, Optional[Role])
    _poll_votes: dict[tuple[int, int, int], PollVotes] = {}

    def track_poll(self, message: discord.Message, role: discord.Role | None = None):
        self._poll_votes[(message.guild.id, message.channel.id, message.id)] = (set(), role)

    async def get_tracked_poll(self, guild_id: int, channel_id: int, message_id: int) -> PollVotes | None:
        if (guild_id, channel_id, message_id) not in self._poll_votes:
            message = await self.get_bot_message(guild_id, channel_id, message_id)
            if message is not None and message.poll:
                role = message.role_mentions[0] if message.role_mentions else None
                user_ids = await _get_poll_votes(message.poll, role)
                self._poll_votes[(guild_id, channel_id, message_id)] = (user_ids, role)

        return self._poll_votes.get((guild_id, channel_id, message_id))

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
        guild_id, channel_id, message_id, user_id = payload.guild_id, payload.channel_id, payload.message_id, payload.user_id

        poll_votes = await self.get_tracked_poll(guild_id, channel_id, message_id)
        if not poll_votes:
            return

        user_ids, role = poll_votes

        if user_id in user_ids:
            return

        member = self.get_guild_member(guild_id, user_id)
        if not member:
            return

        if role and role not in member.roles:
            return

        self._poll_votes[(guild_id, channel_id, message_id)][0].add(user_id)

    async def on_raw_poll_vote_remove(self, payload: discord.RawPollVoteActionEvent):
        guild_id, channel_id, message_id, user_id = payload.guild_id, payload.channel_id, payload.message_id, payload.user_id

        poll_votes = await self.get_tracked_poll(guild_id, channel_id, message_id)
        if not poll_votes:
            return

        self._poll_votes[(guild_id, channel_id, message_id)][0].discard(user_id)

    # endregion

    # region Logging

    async def info(self, guild_id: int, content: str):
        await self._log_level(guild_id, content, "INFO")

    async def error(self, guild_id: int, content: str):
        await self._log_level(guild_id, content, "ERROR")

    async def _log_level(self, guild_id: int, content: str, level: str):
        channel = self.get_guild_channel(guild_id, BOT_LOG_CHANNEL_ID)
        await channel.send(f"[{level}] {content}", allowed_mentions=discord.AllowedMentions.none())

    # endregion

    def _remove_message_cache(self, guild_id: int, channel_id: int, message_id: int):
        self._message_cache.pop((guild_id, channel_id, message_id), None)
        self._react_role_dict.pop((channel_id, message_id), None)
