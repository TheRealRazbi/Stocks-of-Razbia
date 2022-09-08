from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

__all__ = ["Company"]

import random

from sqlalchemy import Column, select, func
from sqlalchemy.sql import sqltypes as t

from utils import create_embed
from .db import Base, AsyncSession, get_object_by_kwargs
from .shares import Shares


class Company(Base):
    __tablename__ = 'company'

    id = Column(t.Integer, primary_key=True)
    full_name = Column(t.String, nullable=False)
    abbv = Column(t.String(4), nullable=False)

    stock_price = Column(t.Float, nullable=False)
    price_diff = Column(t.Float, default=0)
    months = Column(t.Integer, default=0)  # age

    event_increase = Column(t.Integer, default=0)
    event_months_remaining = Column(t.Integer, default=0)

    increase_chance = Column(t.Integer, default=50)  # percentage
    max_increase = Column(t.Float, default=0.3)
    max_decrease = Column(t.Float, default=0.35)

    bankrupt = Column(t.Boolean, default=False)

    shares = relationship("Shares", backref="company", passive_deletes=True)

    # shares = relationship("Shares", backref=backref("company", cascade="all, delete-orphan", single_parent=True), passive_deletes=True)
    # shares = relationship("Shares", backref=backref("company", cascade="save-update, merge, delete, delete-orphan", single_parent=True), passive_deletes=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def iterate(self):
        if self.bankrupt:
            return

        if self.event_increase is None:
            self.event_increase = 0

        if random.randrange(1, 100) < self.increase_chance + self.event_increase:
            amount = random.uniform(1, 1 + self.max_increase)
        else:
            amount = random.uniform(1 - self.max_decrease, 1)

        if self.event_months_remaining is not None:
            self.event_months_remaining -= 1
            if self.event_months_remaining <= 0:
                self.event_increase = 0
                self.max_increase = 0.3

        initial_price = self.stock_price
        self.stock_price = self.stock_price * amount
        self.price_diff = initial_price - self.stock_price

        self.months += 1

        if self.stock_price <= 0.5:
            self.bankrupt = True
            return

        return self.price_diff

    @classmethod
    def create(cls, starting_price, name: tuple = None, **kwargs):
        if name is None:
            name = ["dflt", "default"]
        return cls(
            stock_price=starting_price,
            abbv=name[0].upper(),
            full_name=name[1],
            **kwargs,
        )

    @classmethod
    async def find_by_abbreviation(cls, abbreviation: str, session: AsyncSession):
        return await get_object_by_kwargs(Company, abbv=abbreviation, session=session)

    async def stocks_bought(self, session: AsyncSession):
        query = select([func.sum(Shares.amount)]).where(
            Shares.company_id == self.id
        )
        res = await session.execute(query)
        shares = list(filter(None, res.scalars().all()))
        return sum(shares)

    @property
    def announcement_description(self):
        return f"{self.abbv.upper()}[{self.price_and_price_diff}]"

    @property
    def price_and_price_diff(self) -> str:
        return f"{self.stock_price:,.1f} ({self.price_diff_percent:+.1f}%)"

    def __str__(self):
        years = self.years
        months = self.months % 12
        return f"Name: '{self.abbv}' aka '{self.full_name}' | stock_price: {self.stock_price:,.2f} | " \
               f"price change: {self.price_diff_percent:+.1f}% | " \
               f"lifespan: {years} {'years' if not years == 1 else 'year'} " \
               f"and {months} {'months' if not months == 1 else 'month'}"

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "abbv", "stock_price"),
        )

    @property
    def years(self):
        return self.months // 12 if self.months else 0

    @property
    def price_diff_percent(self) -> int:
        return -(self.price_diff / (self.stock_price + self.price_diff) * 100)

    async def embed(self, session: AsyncSession):
        content = await self.content_for_embed(session=session)
        return create_embed(self.full_name, content=content)

    async def content_for_embed(self, session: AsyncSession) -> dict:
        return {
            'Name': f"{self.abbv} aka {self.full_name}",
            'Stock Price': f'{self.stock_price:.2f}',
            'Price Change': f'{-(self.price_diff / (self.stock_price + self.price_diff) * 100):+.1f}%',
            'Lifespan': f"{f'{self.years} years │ ' if self.years else ''}{self.months % 12} months",
            'Stocks Bought': f'{await self.stocks_bought(session=session):,} shares'
        }

    @staticmethod
    async def get_all_companies(session: AsyncSession, filter_=None, **kwargs):
        query = select(Company).filter_by(**kwargs)
        if filter_:
            query = query.filter(filter_)
        res = await session.execute(query)
        return res.scalars().all()
