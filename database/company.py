from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

__all__ = ["Company"]
import random

from sqlalchemy import Column, select, func
from sqlalchemy.sql import sqltypes as t

from .db import Base
from .shares import Shares


class Company(Base):
    __tablename__ = 'company'

    id = Column(t.Integer, primary_key=True)
    full_name = Column(t.String, nullable=False)
    abbv = Column(t.String(4), nullable=False)

    rich = Column(t.Boolean, default=False)
    stock_price = Column(t.Float)
    price_diff = Column(t.Float, default=0)
    months = Column(t.Integer, default=0)  # age

    increase_chance = Column(t.Integer, default=50)  # percentage
    max_increase = Column(t.Float, default=0.3)
    max_decrease = Column(t.Float, default=0.2)
    decay_rate = Column(t.Float, default=0.015)

    bankrupt = Column(t.Boolean, default=False)

    shares = relationship("Shares", backref="company", passive_deletes=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.price_diff = 0

    def iterate(self):
        if self.bankrupt:
            return

        if random.randrange(1, 100) < self.increase_chance:
            amount = random.uniform(1, 1 + self.max_increase)
        else:
            amount = random.uniform(1 - self.max_decrease, 1)

        initial_price = round(self.stock_price, 2)
        self.stock_price = round(self.stock_price * amount, 2)
        self.price_diff = round(initial_price - self.stock_price, 1)

        self.max_decrease += self.decay_rate
        if self.max_decrease > 1:
            self.max_decrease = 1
        self.months += 1

        if self.stock_price <= 0.5:
            self.bankrupt = True
            return

        return self.price_diff

    @classmethod
    def create(cls, starting_price, name=None, **kwargs):
        if name is None:
            name = ["dflt", "default"]
        return cls(
            stock_price=starting_price,
            abbv=name[0],
            full_name=name[1],
            **kwargs,
        )

    @classmethod
    def find_by_abbreviation(cls, abbreviation: str, session):
        return session.query(cls).filter_by(abbv=abbreviation).first()

    @hybrid_property
    def remaining_shares(self):
        return 100 - sum(share.amount for share in self.shares)

    @remaining_shares.expression
    def remaining_shares(cls):
        return 100 - select([func.sum(Shares.amount)]).where(
            Shares.company_id == cls.id
        ).label("remaining_shares")

    @property
    def announcement_description(self):
        return f"{self.abbv.upper()}[{self.stock_price:.1f}{-(self.price_diff/self.stock_price*100):+.1f}%]"

    def __str__(self):
        years = int(self.months / 12)
        months = self.months % 12
        return f"Name: '{self.abbv}' aka '{self.full_name}' | stock_price: {self.stock_price:.2f} | " \
               f"price change: {-(self.price_diff/self.stock_price*100):+.1f}% | " \
               f"lifespan: {years} {'years' if not years == 1 else 'year'} " \
               f"and {months} {'months' if not months == 1 else 'month'} | Remaining stocks: {self.remaining_shares}"

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "abbv", "rich", "stock_price"),
            # TODO: Change this to include what you want
        )
