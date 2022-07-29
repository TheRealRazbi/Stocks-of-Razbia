from typing import Callable

import discord
from sqlalchemy.orm import Session as SessionType

from database import User


class UserContext:
    __slots__ = ("user", "api", "session", "discord_message", "send_message")

    def __init__(self, user: User, api, session: SessionType, send_message: Callable, discord_message: discord.Message = None):
        self.user = user
        self.api = api
        self.session = session
        self.discord_message = discord_message
        self.send_message = send_message

    def __str__(self):
        return f"{self.user}"




