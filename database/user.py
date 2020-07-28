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

    gain = Column(t.Integer, default=1)
    lost = Column(t.Integer, default=1)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "shares"),
        )

    def points(self, api):
        if api.currency_system == 'streamlabs' and api.tokens_ready:
            url = "https://streamlabs.com/api/v1.0/points"
            querystring = {"access_token": api.streamlabs_token,
                           "username": self.name,
                           "channel": api.name,
                           }
            res = requests.request("GET", url, params=querystring)
            res_json = json.loads(res.text)
            if res.status_code == 200:
                return res_json["points"]
            if res_json["message"].lower() == "user not found":
                print("Looks like you don't have loyalty points enabled, therefore users don't have points, so it errors when tries to fetch the points.")
                input("Please enable streamlabs loyalty points here https://streamlabs.com/dashboard#/loyalty , even if you don't use them, it needs those. Press any key to continue... [it's gonna close itself. open it when you solve it]")
                raise SystemExit
        raise ValueError("Unavailable currency system or tokens not ready")

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

