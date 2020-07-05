from sqlalchemy.orm import Session as SessionType

from database import User


class UserContext:
    __slots__ = ("user", "api", "session")

    def __init__(self, user: User, api, session: SessionType):
        self.user = user
        self.api = api
        self.session = session

    def __str__(self):
        return f"{self.user}"




