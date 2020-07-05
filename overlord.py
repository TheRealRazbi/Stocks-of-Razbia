import time
import random

import sqlalchemy as sql

from API import API
import asyncio
import commands
from bot_commands import register_commands
from contexts import UserContext
from database import User, Company
import database


class Overlord:
    def __init__(self, loop=None):
        database.Base.metadata.create_all()
        self.last_check = time.time()
        self.loop = asyncio.get_event_loop()
        self.api = API(overlord=self, loop=loop)
        # self.iterate_cooldown = 30
        self.iterate_cooldown = 0

        self.max_companies = 10
        self.spawn_ranges = {
            "poor_range": (3, 10),
            "expensive_range": (10, 30),
        }
        self.stock_increase = ''
        self.bankrupt_info = ''

        self.names = {}
        self.load_names()

        self.rich = 0
        self.poor = 0
        self.load_rich_poor()

        self.months = 0

    async def run(self):
        time_since_last_run = time.time() - self.last_check + self.iterate_cooldown  # TODO: remove self.iterate_cooldown
        if time_since_last_run > self.iterate_cooldown*1:
            self.last_check = time.time()
            session = database.Session()

            self.iterate_companies(session)
            self.spawn_companies(session)
            self.clear_bankrupt(session)

            self.display_update(session)
            self.months += 1
            session.close()
        else:
            await asyncio.sleep(0)
            # time.sleep(self.iterate_cooldown-time_since_last_run)

    def spawn_companies(self, session):
        companies_to_spawn = 0
        if session.query(Company).count() < self.max_companies:
            companies_to_spawn = self.max_companies - session.query(Company).count()
            if companies_to_spawn > 5:
                companies_to_spawn = 5

        for _ in range(companies_to_spawn):
            random_abbv = random.choice(list(self.names.items()))
            self.names.pop(random_abbv[0])

            if random.random() > 0.6:
                starting_price = round(random.uniform(*self.spawn_ranges["poor_range"]), 3)
                rich = False
                self.poor += 1
            else:
                starting_price = round(random.uniform(*self.spawn_ranges["expensive_range"]), 3)
                rich = True
                self.rich += 1
            company = Company.create(starting_price, name=random_abbv, rich=rich)
            session.add(company)
        session.commit()

    def iterate_companies(self, session):
        for index_company, company in enumerate(session.query(Company).all()):
            res = company.iterate()
            if res:
                self.stock_increase += f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.2f}"
                self.stock_increase += f"{'+' if company.price_diff >= 0 else ''}{company.price_diff}], "
            else:
                if company.rich:
                    self.rich -= 1
                else:
                    self.poor -= 1
                if not company.abbv == 'DFLT':
                    company.bankrupt = True
                    self.names[company.abbv] = company.full_name
                    session.commit()

    def clear_bankrupt(self, session):
        for index_company, company in enumerate(session.query(Company).filter_by(bankrupt=True)):
            if index_company == 0:
                self.bankrupt_info += "The following companies bankrupt: "
            self.bankrupt_info += f'{company.abbv.upper()}, '
            session.delete(company)
            session.commit()

    def load_names(self):
        session = database.Session()
        companies = session.query(Company).all()
        with open("company_names.txt", "r") as f:
            for line in f:
                temp = line.strip().split('|')
                if temp[0].strip():
                    self.names[temp[1].upper()] = temp[0].capitalize()
        for company in companies:
            self.names.pop(company.abbv, None)

        session.close()

    def load_rich_poor(self):
        session = database.Session()
        for data in session.query(
                Company.rich,
                sql.func.count()
        ).group_by(Company.rich).all():
            rich, count = data
            if rich:
                self.rich = count
            else:
                self.poor = count
        session.close()

    def display_update(self, session):
        if self.stock_increase:
            self.api.send_chat_message(self.stock_increase[:-2])
            self.stock_increase = ''
        self.api.send_chat_message(f"Companies: {session.query(Company).count()}/{self.max_companies} Rich: {self.rich}"
                                   f", Poor: {self.poor}, Most Expensive Company: {self.most_expensive_company(session)}")
        if self.bankrupt_info:
            self.api.send_chat_message(self.bankrupt_info[:-2])
            self.bankrupt_info = ''

    @staticmethod
    def find_company(abbreviation: str, session):
        return session.query(Company).filter_by(abbv=abbreviation).first()

    @staticmethod
    def most_expensive_company(session):
        stock_price = 0
        most_expensive = None
        for company in session.query(Company).all():
            if company.stock_price > stock_price:
                stock_price = company.stock_price
                most_expensive = company
        return most_expensive

    def delete_table_contents(self, table, session=None):
        local_session = False
        if session is None:
            session = database.Session()
            local_session = True
        session.query(table).delete()
        if table == database.Company:
            self.rich = 0
            self.poor = 0
        session.commit()
        if local_session:
            session.close()

    def delete_all(self):
        session = database.Session()
        self.delete_table_contents(database.Company, session=session)
        self.delete_table_contents(database.User, session=session)
        self.delete_table_contents(database.Shares, session=session)
        session.close()


if __name__ == '__main__':
    def start(func, overlord):
        return overlord.loop.run_until_complete(func)

    def test_basic_share(session):
        user = database.User(name='razbith3player')
        company = database.Company.create(5)
        session.add(user)
        session.add(company)
        share = database.Shares(user=user, company=company, amount=69)
        session.add(share)
        session.commit()

    def test_iteration(overlord: Overlord, months=60):
        now = time.time()
        while overlord.months <= months:
            start(overlord.run(), overlord)
        print(f"{months} months took {round(time.time()-now, 3)}")

    o = Overlord()
    register_commands(o.api)
    # session = database.Session()
    # user = session.query(User).get(1)
    # print(user.points(o.api))
    # print(o.api.subtract_points(user.name, -1))
    # print(user.points(o.api))

    # o.delete_all()
    start(o.api.start_read_chat(), o)
    # start(test_iteration(o), o)

    # start(o.api.send_chat_message('hello'), o)
    # session = database.Session()
    # session.delete(session.query(Company).get(1))
    # session.commit()

    # user = User('razbith3player', o)
    # ctx = UserContext(user, o.api)
    # amount = 100
    # company_abbv = 'GOLD'
    # commands.buy_stocks(ctx, amount, company_abbv)










