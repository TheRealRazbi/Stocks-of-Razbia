__all__ = ["User"]

import math

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Column, select
from sqlalchemy.sql import sqltypes as t
from sqlalchemy.orm import relationship

import requests

import database
from .db import Base, Session
from .company import Company
from .shares import Shares
import json


class User(Base):
    __tablename__ = 'user'

    id = Column(t.Integer, primary_key=True)
    name = Column(t.String, nullable=False)
    discord_id = Column(t.String)

    gain = Column(t.Integer, default=1)
    lost = Column(t.Integer, default=1)
    new = Column(t.Boolean, default=True)
    last_worth_checked = Column(t.Integer, default=0)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "discord_id", "shares", "gain", "lost"),
        )

    def stocks_worth(self, session: database.Session) -> int:
        worth = 0
        shares = self.get_all_owned_stocks(session=session)
        for share in shares:
            company = session.query(Company).get(share.company_id)
            worth += math.ceil(share.amount*company.stock_price)
        return worth

    async def total_worth(self, api, session: database.Session) -> int:
        points = await self.points(api=api, session=session)
        worth = points + self.stocks_worth(session=session)

        return worth

    async def points(self, api, session: database.Session) -> int:
        user = session.query(User).get(self.id)
        if hasattr(api, 'fake_points'):
            return api.fake_points
        if api.use_local_points_instead:
            with open("points.json", "r") as f:
                points_db = json.load(f)

            if self.name not in points_db:
                points_db[self.name] = 1_000

                # testers_without_twitch = ('swavyL',)
                # testers_discord_ids = ('757834005390426222', '916526447521308712', '779363710505582654', '534388740966187038')
                with open("points.json", "w") as f:
                    json.dump(points_db, f)

            points = points_db[self.name]
            user.last_worth_checked = points + user.stocks_worth(session=session)
            session.commit()
            return points

            # if self.name in testers_without_twitch or self.discord_id in testers_discord_ids:
            #     return 1_000_000

        if await api.tokens_ready:
            if api.currency_system == 'streamlabs':
                url = "https://streamlabs.com/api/v1.0/points"
                querystring = {"access_token": api.streamlabs_key,
                               "username": self.name,
                               "channel": api.channel_name,
                               }
                res = requests.get(url, params=querystring)
                if res.status_code == 200:
                    points = res.json()["points"]
                    user.last_worth_checked = points + user.stocks_worth(session=session)
                    session.commit()
                    return points
                elif res.status_code == 404:
                    return 0
                # if res.json()["message"].lower() == "user not found":
                #     print("Looks like you don't have loyalty points enabled, therefore users don't have points, so it errors when tries to fetch the points.")
                #     input("Please enable streamlabs loyalty points here https://streamlabs.com/dashboard#/loyalty , even if you don't use them, it needs those. Press any key to continue... [it's gonna close itself. open it when you solve it]")
                #     raise SystemExit
                elif res.status_code >= 500:
                    print(
                        "streamlabs server errored or... something. better tell Razbi, although its probably a Streamlabs thing. "
                        "to prevent screwing people's points, the program will shutdown as you press Enter")
                    input("Press 'enter' to quit")

            elif api.currency_system == 'stream_elements':
                url = f'https://api.streamelements.com/kappa/v2/points/{await api.stream_elements_id()}/{self.name}'
                headers = {'Authorization': f'OAuth {api.stream_elements_key}'}
                res = requests.get(url, headers=headers)
                if res.status_code == 200:
                    points = res.json()['points']
                    user.last_worth_checked = points + user.stocks_worth(session=session)
                    session.commit()
                    return points
                elif res.status_code == 400:
                    return 0
                elif res.status_code >= 500:
                    print(
                        "stream_elements server errored or... something. better tell Razbi, although its probably a stream_elements thing. "
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

    def get_all_owned_stocks(self, session: Session):
        query = select(database.Shares).where(database.Shares.user_id == self.id)
        query = session.execute(query)
        return query.scalars().all()

    async def profit_str(self, api, session: Session):
        gain, lost = self.gain, self.lost
        gain += await self.total_worth(api=api, session=session)
        profit = f'{gain - lost:+}'
        symbol = '+'
        try:
            if lost > gain:
                symbol = '-'
                # gain, lost = lost, gain

            gain, lost = abs(gain), abs(lost)
            percentage_profit = f'{symbol}{abs((gain / lost) * 100 - 100):.0f}% ''of {currency_name} invested.'
        except ZeroDivisionError:
            percentage_profit = f'0%'
        return profit, percentage_profit

    def passive_income(self, company: Company, session: Session) -> int:
        if share := session.query(Shares).get((self.id, company.id)):
            value_of_stocks = math.ceil(share.amount * company.stock_price)
            income_percent = 0.10 - (value_of_stocks / 5_000) / 100
            return math.ceil(value_of_stocks * max(income_percent, 0.01))
        return 0

    def refresh(self, session: database.Session):
        return session.query(User).get(self.id)

    @property
    def discord_mention(self) -> str:
        return f'<@{self.discord_id}>'
