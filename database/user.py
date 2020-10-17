__all__ = ["User"]

import math

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Column
from sqlalchemy.sql import sqltypes as t
from sqlalchemy.orm import relationship

import requests
import asyncio

from .db import Base, Session
from .company import Company


class User(Base):
    __tablename__ = 'user'

    id = Column(t.Integer, primary_key=True)
    name = Column(t.String, nullable=False)

    gain = Column(t.Integer, default=1)
    lost = Column(t.Integer, default=1)
    new = Column(t.Boolean, default=True)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "shares", "gain", "lost"),
        )

    async def points(self, api):
        if hasattr(api, 'fake_points'):
            return api.fake_points
        if api.tokens_ready:
            if api.currency_system == 'streamlabs':
                url = "https://streamlabs.com/api/v1.0/points"
                querystring = {"access_token": api.streamlabs_key,
                               "username": self.name,
                               "channel": api.name,
                               }
                res = requests.get(url, params=querystring)
                if res.status_code == 200:
                    return res.json()["points"]
                # if res.json()["message"].lower() == "user not found":
                #     print("Looks like you don't have loyalty points enabled, therefore users don't have points, so it errors when tries to fetch the points.")
                #     input("Please enable streamlabs loyalty points here https://streamlabs.com/dashboard#/loyalty , even if you don't use them, it needs those. Press any key to continue... [it's gonna close itself. open it when you solve it]")
                #     raise SystemExit
                elif res.status_code >= 500:
                    print("streamlabs server errored or... something. better tell Razbi, although its probably a Streamlabs thing. "
                          "to prevent screwing people's points, the program will shutdown as you press Enter")
                    input("Press 'enter' to quit")

            elif api.currency_system == 'stream_elements':
                url = f'https://api.streamelements.com/kappa/v2/points/{api.stream_elements_id}/{self.name}'
                headers = {'Authorization': f'OAuth {api.stream_elements_key}'}
                res = requests.get(url, headers=headers)
                if res.status_code == 200:
                    return res.json()['points']
                elif res.status_code >= 500:
                    print("stream_elements server errored or... something. better tell Razbi, although its probably a stream_elements thing. "
                          "to prevent screwing people's points, the program will shutdown as you press Enter")
                else:
                    raise ValueError(
                        f"Error encountered while getting points from user {self.name} with stream_elements system. HTTP Code {res.status_code}. "
                        "Please tell Razbi about it.")

            elif api.currency_system == 'streamlabs_local':
                return int(await api.request_streamlabs_local_message(f'!get_user_points {self.name}'))

            raise ValueError(f"Unavailable Currency System: {api.currency_system}")
        raise ValueError("Tokens not ready for use. Tell Razbi about this.")

    @hybrid_property
    def profit(self):
        return self.gain - self.lost

    @property
    def profit_str(self):
        gain, lost = self.gain, self.lost
        for share in self.shares:
            company: Company = share.company
            value_of_owned_stocks = math.ceil(company.stock_price*share.amount)
            gain += value_of_owned_stocks
            lost -= value_of_owned_stocks
        profit = f'{gain - lost:+}'
        symbol = '+'
        try:
            if lost > gain:
                symbol = '-'
                gain, lost = lost, gain
            percentage_profit = f'{symbol}{(gain / lost * 100 - 100):.0f}% ''of {currency_name} invested.'
        except ZeroDivisionError:
            percentage_profit = f'0%'
        return profit, percentage_profit

