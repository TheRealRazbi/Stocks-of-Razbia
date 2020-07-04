

class UserContext:
    __slots__ = ("user", "api", "session")

    def __init__(self, user, api, session):
        self.user = user
        self.api = api
        self.session = session

    def __str__(self):
        return f"{self.user}"




