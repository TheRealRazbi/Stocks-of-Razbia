from company import Company
import time
import random
from API import API
import asyncio
import commands
from contexts import UserContext
from user import User
import database


class Overlord:
    def __init__(self, loop=None):
        self.last_check = time.time()
        self.loop = asyncio.get_event_loop()
        self.api = API(overlord=self, loop=loop)
        # self.iterate_cooldown = 30
        self.iterate_cooldown = 0
        self.companies = {
            "active_companies": [],
            "bankrupt_companies": [],
        }
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

        self.months = 0

    def run(self):
        time_since_last_run = time.time() - self.last_check + self.iterate_cooldown  # TODO: remove self.iterate_cooldown
        if time_since_last_run > self.iterate_cooldown*1:
            self.last_check = time.time()

            self.iterate_companies()
            self.spawn_companies()
            self.clear_bankrupt()

            self.display_update()
            self.months += 1
        else:
            time.sleep(0)
            # time.sleep(self.iterate_cooldown-time_since_last_run)

    def spawn_companies(self):
        companies_to_spawn = 0
        if len(self.companies["active_companies"]) < self.max_companies:
            companies_to_spawn = self.max_companies - len(self.companies["active_companies"])
            if companies_to_spawn > 5:
                companies_to_spawn = 5

        for _ in range(companies_to_spawn):
            random_abbv = random.choice(list(self.names.items()))
            self.names.pop(random_abbv[0])

            if random.random() > 0.6:
                starting_price = round(random.uniform(*self.spawn_ranges["poor_range"]), 3)
                rich = False
            else:
                starting_price = round(random.uniform(*self.spawn_ranges["expensive_range"]), 3)
                rich = True
            self.companies["active_companies"].append(Company(starting_price, overlord=self, rich=rich, name=random_abbv))

    def iterate_companies(self):
        for index_company, company in enumerate(self.companies["active_companies"]):
            res = company.iterate()
            if res:
                self.stock_increase += f"{company.abbv.upper()}[{company.stock_price-company.price_diff}"
                self.stock_increase += f"{'+' if company.price_diff >= 0 else ''}{company.price_diff}], "
            else:
                if company.rich:
                    self.rich -= 1
                else:
                    self.poor -= 1
                if not company.abbv == 'DFLT':
                    self.names[company.abbv] = company.full_name
                    self.companies["active_companies"].remove(self)
                    self.companies["bankrupt_companies"].append(self)

    def clear_bankrupt(self):
        for index_company, company in enumerate(self.companies["bankrupt_companies"]):
            if index_company == 0:
                self.bankrupt_info += "The following companies bankrupt: "
            self.bankrupt_info += f'{company.abbv.upper()}, '
            self.companies["bankrupt_companies"].remove(company)

    def load_names(self):
        with open("lib/company_names.txt", "r") as f:
            for line in f:
                temp = line.strip().split('|')
                if temp[0].strip():
                    self.names[temp[1].upper()] = temp[0].capitalize()

    def display_update(self):
        if self.stock_increase:
            print(self.stock_increase[:-2])
            self.stock_increase = ''
        print(f"Companies: {len(self.companies['active_companies'])}/{self.max_companies} Rich: {self.rich}"
              f", Poor: {self.poor}, Most Expensive Company: {self.most_expensive_company}")
        if self.bankrupt_info:
            print(self.bankrupt_info[:-2])
            self.bankrupt_info = ''

    def find_company(self, abbreviation: str):
        abbreviation = abbreviation.upper()
        for company in self.companies["active_companies"]:
            if company.abbv == abbreviation:
                return company

    @property
    def most_expensive_company(self):
        stock_price = 0
        most_expensive = None
        for company in self.companies["active_companies"]:
            if company.stock_price > stock_price:
                stock_price = company.stock_price
                most_expensive = company
        return most_expensive

    def buy_stocks(self, amount, user):
        pass


if __name__ == '__main__':
    def start(func, overlord):
        return overlord.loop.run_until_complete(func)

    o = Overlord()
    # user = User('razbith3player', o)
    # ctx = UserContext(user, o.api)
    # amount = 100
    # company_abbv = 'GOLD'
    # commands.buy_stocks(ctx, amount, company_abbv)
    database.Base.metadata.create_all(database.engine)
    session = database.Session()
    session.add(User('razbith3player', o))
    session.add(Company(5, o))
    session.add(database.SharesDB(session.query(User).filter_by(name='razbith3player').first(),
                                  session.query(Company).filter_by(full_name='default').first(),
                                  100))
    print(session.query(database.SharesDB).filter_by(user_id='razbith3player'))

    # months = 10
    # while True:
    # now = time.time()
    # while o.months <= months:
    #     o.run()
    # print(f"{months} months took {round(time.time()-now, 3)}")








