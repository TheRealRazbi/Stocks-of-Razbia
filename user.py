from collections import defaultdict
from sqlalchemy import Column, Integer, String
import database


class User(database.Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    def __init__(self, name, overlord, **kwargs):
        self.overlord = overlord
        self.name = name
        kwargs[name] = name
        super().__init__(**kwargs)

        # self.owned_stocks = defaultdict(int)

    def points(self, session):

        return  # TODO: Add a way to fetch user's points

    def __eq__(self, other):
        if isinstance(other, User):
            other = other.name
        if self.name == other:
            return True
        return False

    def __str__(self):
        return f'Username: "{self.name}"'


if __name__ == '__main__':
    pass
