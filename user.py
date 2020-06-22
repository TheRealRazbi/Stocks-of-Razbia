from collections import defaultdict


class User:
    def __init__(self, name, overlord):
        self.overlord = overlord
        self.name = name
        self.owned_stocks = defaultdict(int)

    @property
    def points(self):
        return  # TODO: Add a way to fetch user's points

    def __eq__(self, other):
        if isinstance(other, User):
            other = other.name
        if self.name == other:
            return True
        return False


if __name__ == '__main__':
    pass

