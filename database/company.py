from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

__all__ = ["Company"]
import random

from sqlalchemy import Column, select, func
from sqlalchemy.sql import sqltypes as t

from utils import create_embed
from .db import Base
from .shares import Shares


class Company(Base):
    __tablename__ = 'company'

    id = Column(t.Integer, primary_key=True)
    full_name = Column(t.String, nullable=False)
    abbv = Column(t.String(4), nullable=False)

    stock_price = Column(t.Float)
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
    def find_by_abbreviation(cls, abbreviation: str, session):
        return session.query(cls).filter_by(abbv=abbreviation).first()

    @hybrid_property
    def stocks_bought(self) -> int:
        # noinspection PyTypeChecker
        return sum(share.amount for share in self.shares)

    @stocks_bought.expression
    def stocks_bought(self):
        return select([func.sum(Shares.amount)]).where(
            Shares.company_id == self.id
        ).label("stocks_bought")

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
               f"and {months} {'months' if not months == 1 else 'month'} | Stocks Bought: {self.stocks_bought}"

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "abbv", "stocks_bought", "stock_price"),
        )

    @property
    def years(self):
        return self.months // 12 if self.months else 0

    @property
    def price_diff_percent(self) -> int:
        return -(self.price_diff / (self.stock_price + self.price_diff) * 100)

    @property
    def embed(self):
        content = self.content_for_embed
        return create_embed(self.full_name, content=content)

    @property
    def content_for_embed(self) -> dict:
        return {
            'Name': f"{self.abbv} aka {self.full_name}",
            'Stock Price': f'{self.stock_price:.2f}',
            'Price Change': f'{-(self.price_diff / (self.stock_price + self.price_diff) * 100):+.1f}%',
            'Lifespan': f"{f'{self.years} years │ ' if self.years else ''}{self.months % 12} months",
            'Stocks Bought': f'{self.stocks_bought:,} shares'
        }
