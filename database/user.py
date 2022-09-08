__all__ = ["User"]

import math

import requests
from sqlalchemy import Column, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as t

import database
from .company import Company
from .db import Base, Session, AsyncSession
from .shares import Shares


class User(Base):
    __tablename__ = 'user'

    id = Column(t.Integer, primary_key=True)
    name = Column(t.String, nullable=False)
    discord_id = Column(t.String)

    gain = Column(t.Integer, default=1)
    lost = Column(t.Integer, default=1)
    new = Column(t.Boolean, default=True)
    local_points = Column(t.Integer, default=1000)
    last_most_stocks_worth_checked = Column(t.Integer, default=0)
    last_most_stocks_owned_checked = Column(t.Integer, default=0)
    last_balance_checked = Column(t.Integer, default=0)
    last_worth_checked = Column(t.Integer, default=0)
    last_income_checked = Column(t.Integer, default=0)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "discord_id", "shares", "gain", "lost"),
        )

    async def stocks_worth(self, session: AsyncSession) -> int:
        worth = 0
        shares = await self.get_all_owned_stocks(session=session)
        how_many = 0
        for share in shares:
            if company := await session.get(Company, share.company_id):
                worth += math.ceil(share.amount * company.stock_price)
                how_many += share.amount
        self.last_most_stocks_worth_checked = worth
        self.last_most_stocks_owned_checked = how_many
        await session.commit()
        return worth

    async def total_worth(self, api, session: database.AsyncSession) -> int:
        points = await self.points(api=api, session=session)
        worth = points + await self.stocks_worth(session=session)
        self.last_worth_checked = worth
        await session.commit()
        return worth

    async def points(self, api, session: database.AsyncSession) -> int:
        user = await session.get(User, self.id)
        if hasattr(api, 'fake_points'):
            return api.fake_points
        if api.use_local_points_instead:
            if self.local_points is None:
                self.local_points = 1000

            points = user.local_points
            user.last_balance_checked = points
            user.last_worth_checked = points + await user.stocks_worth(session=session)
            await session.commit()
            return points

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
                    user.last_balance_checked = points
                    user.last_worth_checked = points + user.stocks_worth(session=session)
                    await session.commit()
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
                    user.last_balance_checked = points
                    user.last_worth_checked = points + user.stocks_worth(session=session)
                    await session.commit()
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

    async def get_all_owned_stocks(self, session: AsyncSession):
        query = select(database.Shares).where(database.Shares.user_id == self.id)
        scalars = await session.scalars(query)
        return scalars.all()

    async def profit_str(self, api, session: AsyncSession) -> str:
        gain, lost = self.gain, self.lost
        gain += await self.total_worth(api=api, session=session)
        profit = f'{gain - lost:+,}'
        return profit
        # symbol = '+'
        # try:
        #     if lost > gain:
        #         symbol = '-'
        #         # gain, lost = lost, gain
        #
        #     gain, lost = abs(gain), abs(lost)
        #     percentage_profit = f'{symbol}{abs((gain / lost) * 100 - 100):.0f}% ''of {currency_name} invested.'
        # except ZeroDivisionError:
        #     percentage_profit = f'0%'

    async def passive_income(self, company: Company, session: AsyncSession) -> int:
        if share := await session.get(Shares, (self.id, company.id)):
            value_of_stocks = math.ceil(share.amount * company.stock_price)
            income = 0
            stacks_of_5k = value_of_stocks // 5000
            left_overs = value_of_stocks % 5000
            for cycle in range(stacks_of_5k):
                income_percent = max(((10 - cycle) / 100), 0.01)
                income += 5000 * income_percent

            income += left_overs * max(((10 - stacks_of_5k) / 100), 0.01)

            return math.ceil(income)

            # income_percent = 0.10 - (value_of_stocks / 5_000) / 100
            # return math.ceil(value_of_stocks * max(income_percent, 0.01))
        return 0

    async def refresh(self, session: database.AsyncSession):
        return await session.get(User, self.id)

    @property
    def discord_mention(self) -> str:
        return f'<@{self.discord_id}>'

    async def update_last_checked_income(self, session) -> None:
        user = await self.refresh(session=session)
        total_income = 0
        shares = await user.get_all_owned_stocks(session)
        for share in shares:
            if company := await session.get(Company, share.company_id):
                specific_income = await user.passive_income(company, session)
                total_income += specific_income
        user.last_income_checked = total_income
        await session.commit()
