import random
from decimal import *
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import database


class Company(database.Base):
    __tablename__ = 'company'

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    abbreviation = Column(String(4), nullable=False)

    def __init__(self, starting_price, overlord, rich=False, name=None, **kwargs):
        self.overlord = overlord
        if name is None:
            name = ["dflt", "default"]
        self.abbv = name[0]
        self.full_name = name[1]
        kwargs['full_name'] = self.full_name
        kwargs['abbreviation'] = self.abbv
        super().__init__(**kwargs)

        if self.abbv != 'dflt':
            overlord.names[self.abbv] = self.full_name

        self.stock_price = Decimal(starting_price)
        self.price_diff = 0
        self.chances = {
            "increase_chance": 50,
            "max_increase": 0.2,
            "max_decrease": 0.2,
            "decay_rate": 0.015
        }
        self.bankrupt = False
        if rich:
            overlord.rich += 1
        else:
            overlord.poor += 1
        self.rich = rich
        self.owners = set([])

    def iterate(self):
        if self.bankrupt:
            return

        if random.randrange(1, 100) > self.chances["increase_chance"]:
            amount = random.uniform(1, 1+self.chances["max_increase"])
        else:
            amount = random.uniform(1-self.chances["max_decrease"], 1)

        initial_price = round(self.stock_price, 2)
        self.stock_price = round(self.stock_price * Decimal(amount), 2)
        self.price_diff = round(initial_price-self.stock_price, 2)

        self.chances["max_decrease"] += self.chances["decay_rate"]
        if self.chances["max_decrease"] > 1:
            self.chances["max_decrease"] = 1

        if self.stock_price <= 0.5:
            self.bankrupt = True
            return

        return self.price_diff

    @property
    def market_cap(self):
        return round(self.stock_price*100)

    def __repr__(self):
        return f"Name: '{self.abbv}' aka '{self.full_name}' | stock_price: {self.stock_price:.2f} | total_value: {self.market_cap}"

    @property
    def bankrupt(self):
        return self._bankrupt

    @bankrupt.setter
    def bankrupt(self, other):
        self._bankrupt = other
        if other:
            self.clear()

    def clear(self):
        if self.rich:
            self.overlord.rich -= 1
        else:
            self.overlord.poor -= 1
        if not self.abbv == 'DFLT':
            self.overlord.names[self.abbv] = self.full_name
            self.overlord.companies["active_companies"].remove(self)
            self.overlord.companies["bankrupt_companies"].append(self)


if __name__ == '__main__':
    # c = Company(15, None)
    # for i in range(12):
    #     c.iterate()
    #     print(c)
    pass


