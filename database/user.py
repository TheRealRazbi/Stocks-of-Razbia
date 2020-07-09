from sqlalchemy import Column
from sqlalchemy.sql import sqltypes as t
from sqlalchemy.orm import relationship

import requests
import json

from .db import Base


class User(Base):
    __tablename__ = 'user'

    id = Column(t.Integer, primary_key=True)
    name = Column(t.String, nullable=False)

    gain = Column(t.Integer, default=0)
    lost = Column(t.Integer, default=0)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "shares"),
        )

    def points(self, api):
        url = "https://streamlabs.com/api/v1.0/points"
        querystring = {"access_token": api.streamlabs_token,
                       "username": self.name,
                       "channel": api.name,
                       }
        return json.loads(requests.request("GET", url, params=querystring).text)["points"]

    @property
    def profit_str(self):
        profit = f'{self.gain - self.lost:+}'
        symbol = '+'
        gain, lost = self.gain, self.lost
        try:
            if self.lost > self.gain:
                symbol = '-'
                gain, lost = lost, gain
            percentage_profit = f'{symbol}{(gain / lost * 100):.0f}% of points invested'
        except ZeroDivisionError:
            percentage_profit = f'0%'
        return profit, percentage_profit

