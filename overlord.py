import time
import random
from API import API
import asyncio
import commands
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
        companies = session.query(Company).all()
        for company in companies:
            if company.rich:
                self.rich += 1
            else:
                self.poor += 1
        session.close()

    def display_update(self, session):
        if self.stock_increase:
            print(self.stock_increase[:-2])
            self.stock_increase = ''
        print(f"Companies: {session.query(Company).count()}/{self.max_companies} Rich: {self.rich}"
              f", Poor: {self.poor}, Most Expensive Company: {self.most_expensive_company(session)}")
        if self.bankrupt_info:
            print(self.bankrupt_info[:-2])
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

    def buy_stocks(self, amount, user):
        pass

    def delete_all(self):
        session = database.Session()
        companies = session.query(database.Company).all()
        for company in companies:
            session.delete(company)
        users = session.query(database.User).all()
        for user in users:
            session.delete(user)
        session.commit()
        self.rich = 0
        self.poor = 0


if __name__ == '__main__':
    def start(func, overlord):
        return overlord.loop.run_until_complete(func)

    def test_basic_share(session):
        session.add(database.Company.create(5))
        session.add(database.User(name='razbith3player'))
        user = session.query(User).get(1)
        company = session.query(Company).get(1)
        share = database.Shares(user=user, company=company, amount=69)
        session.add(share)
        session.commit()

    o = Overlord()
    # o.delete_all()

    # session = database.Session()
    # session.delete(session.query(Company).get(1))
    # session.commit()

    # user = User('razbith3player', o)
    # ctx = UserContext(user, o.api)
    # amount = 100
    # company_abbv = 'GOLD'
    # commands.buy_stocks(ctx, amount, company_abbv)

    months = 60
    now = time.time()
    while o.months <= months:
        start(o.run(), o)
    print(f"{months} months took {round(time.time()-now, 3)}")








