from sqlalchemy.orm import relationship, backref

__all__ = ["Company"]
import random

from sqlalchemy import Column
from sqlalchemy.sql import sqltypes as t

from .db import Base


class Company(Base):
    __tablename__ = 'company'

    id = Column(t.Integer, primary_key=True)
    full_name = Column(t.String, nullable=False)
    abbv = Column(t.String(4), nullable=False)

    rich = Column(t.Boolean, default=False)
    stock_price = Column(t.Float)
    months = Column(t.Integer, default=0)  # age

    increase_chance = Column(t.Integer, default=50)  # percentage
    max_increase = Column(t.Float, default=0.2)
    max_decrease = Column(t.Float, default=0.2)
    decay_rate = Column(t.Float, default=0.015)

    bankrupt = Column(t.Boolean, default=False)

    shares = relationship("Shares", backref="company", passive_deletes=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price_diff = 0

    def iterate(self):
        if self.bankrupt:
            return

        if random.randrange(1, 100) > self.increase_chance:
            amount = random.uniform(1, 1 + self.max_increase)
        else:
            amount = random.uniform(1-self.max_decrease, 1)

        initial_price = round(self.stock_price, 2)
        self.stock_price = round(self.stock_price * amount, 2)
        self.price_diff = round(initial_price - self.stock_price, 2)

        self.max_decrease += self.decay_rate
        if self.max_decrease > 1:
            self.max_decrease = 1
        self.months += 1

        if self.stock_price <= 0.5:
            self.bankrupt = True
            return

        return self.price_diff

    @property
    def market_cap(self):
        return round(self.stock_price*100)

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

    def __str__(self):
        return f"Name: '{self.abbv}' aka '{self.full_name}' "\
               f"| stock_price: {self.stock_price:.2f} | age: {self.months} months"

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "abbv", "rich", "stock_price"),
            # TODO: Change this to include what you want
        )


if __name__ == '__main__':
    pass
