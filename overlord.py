import time
import random

import sqlalchemy as sql

from API import API
import asyncio
# import commands
from bot_commands import register_commands
# from contexts import UserContext
from database import User, Company
import database
import custom_tools
from termcolor import colored
import math


class Overlord:
    def __init__(self, loop=None):
        database.Base.metadata.create_all()
        self.last_check = 0
        self.loop = asyncio.get_event_loop()
        self.api = API(overlord=self, loop=loop)
        register_commands(self.api)
        self.iterate_cooldown = 30*60
        # self.iterate_cooldown = 3

        self.max_companies = 10
        self.spawn_ranges = {
            "poor_range": (3, 10),
            "expensive_range": (10, 30),
        }
        self.stock_increase = []
        self.bankrupt_info = []
        self.owners_of_bankrupt_companies = set()

        self.names = {}
        self.load_names()
        self.load_currency_name()

        self.rich = 0
        self.poor = 0
        self.load_rich_poor()

        self.load_age()

    async def run(self):
        time_since_last_run = time.time() - self.last_check
        if time_since_last_run > self.iterate_cooldown:
            self.last_check = time.time()
            session = database.Session()

            self.iterate_companies(session)
            self.spawn_companies(session)
            self.clear_bankrupt(session)

            self.display_update(session)
            self.months += 1
            self.update_age()
            session.close()
        else:
            await asyncio.sleep(3)
            # time.sleep(self.iterate_cooldown-time_since_last_run)

    def spawn_companies(self, session):
        companies_to_spawn = 0
        if session.query(Company).count() < self.max_companies:
            companies_to_spawn = self.max_companies - session.query(Company).count()
            if companies_to_spawn > 5:
                companies_to_spawn = 5
        if session.query(Company).count() == 0 and companies_to_spawn == 5:
            print(colored("hint: you can type the commands only in your twitch chat", "green"))
            self.api.send_chat_message("First 5 companies spawned. use '!company all' to see them.")

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
                stock_increase = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}"\
                                 f"{'+' if company.price_diff >= 0 else ''}{company.price_diff}]"
                self.stock_increase.append(stock_increase)
                shares = session.query(database.Shares).filter_by(company_id=company.id)
                for share in shares:
                    cost = math.ceil(math.ceil(share.amount*company.stock_price)*.1)
                    user = session.query(User).get(share.user_id)
                    self.api.subtract_points(user.name, -cost)

                session.commit()
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
            self.bankrupt_info.append(f'{company.abbv.upper()}')
            shares = session.query(database.Shares).filter_by(company_id=company.id).all()
            for share in shares:
                user = session.query(database.User).get(share.user_id)
                self.api.subtract_points(user.name, -share.amount)
                self.owners_of_bankrupt_companies.add(f'@{user.name}')
                # print(f"Refunded {share.amount} points to @{user.name}")
            session.delete(company)
            session.commit()

    def load_names(self):
        session = database.Session()
        companies = session.query(Company).all()
        with open("lib/code/company_names.txt", "r") as f:
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

    def load_age(self):
        try:
            with open("lib/age", "r") as f:
                self.months = int(f.read().strip())
        except FileNotFoundError:
            with open("lib/age", "w") as f:
                f.write('0')
            self.load_age()

    def update_age(self):
        with open("lib/age", "w") as f:
            f.write(str(self.months))

    def display_update(self, session):
        if self.stock_increase:
            companies_to_announce, owners = self.get_companies_for_updates(session)
            # self.api.send_chat_message(f'Month: {self.months} | {", ".join(self.stock_increase)}')
            self.api.send_chat_message(f'Year: {int(self.months/12)} | Month: {self.months%12} | '
                                       f'{", ".join(companies_to_announce)} {" ".join(owners)} | '
                                       f'Use "!company all" to display all of them.')
            self.stock_increase = []
        # self.api.send_chat_message(f"Companies: {session.query(Company).count()}/{self.max_companies} Rich: {self.rich}"
        #                            f", Poor: {self.poor}, Most Expensive Company: {self.most_expensive_company(session)}")
        if self.bankrupt_info:
            self.api.send_chat_message(f'The following companies bankrupt: {", ".join(self.bankrupt_info)} '
                                       f'{" ".join(self.owners_of_bankrupt_companies)}')
            self.bankrupt_info = []

    @staticmethod
    def get_companies_for_updates(session):
        res = []
        owners = session.query(database.User).filter(database.User.shares).all()
        owners = [f'@{user.name}' for user in owners]

        for company in session.query(Company).filter(Company.shares).all():
            if len(res) >= 5:
                break
            message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
            res.append(message)

        if len(res) < 3:
            richest_companies = session.query(database.Company).order_by(Company.stock_price.desc()).limit(3-len(res)).all()
            for company in richest_companies:
                # message = f"{company.abbv.upper()}[{company.stock_price - company.price_diff:.1f}{company.price_diff:+}]"
                message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff / company.stock_price * 100:+.1f}%]"
                if company.stock_price < 0:
                    print("A company has like stock_price under 0, I have absolutely no idea how was this possible, please tell Razbi about it")
                if message not in res:
                    res.append(message)
        return res, owners

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

    def main_loop(self):
        pass

    def load_currency_name(self):
        try:
            with open("lib/currency_name", "r") as f:
                self.currency_name = f.read().strip()
        except FileNotFoundError:
            with open("lib/currency_name", "w") as f:
                res = custom_tools.validate_input("How would you want to call your points? E.g.: 'points', 'souls', 'bullets': ", color='green', character_min=4)
                f.write(res)
                print(f'{colored(f"Points alias called {res} was saved successfully", "yellow")}')
            self.load_currency_name()

    @staticmethod
    def display_credits():
        print(f"""
--------------------------------------------------------------------------
Welcome to {colored('Stocks of Razbia', 'green')}
This program is open-source and you can read the code at {colored('https://github.com/TheRealRazbi/Stocks-of-Razbia', 'yellow')}
In fact you can even read the code by opening {colored('lib/code/', 'green')}
You can check for updates when you start the program and pick the other option.
This program was made by {colored('Razbi', 'magenta')} and {colored('Nesami', 'magenta')}
Program started at {colored(str(time.strftime('%H : %M')), 'cyan')}
--------------------------------------------------------------------------\n
        """)


def start(func, overlord):
    return overlord.loop.run_until_complete(func)


async def iterate_forever(overlord: Overlord):
    await asyncio.sleep(5)
    now = time.time()
    # while overlord.months <= months:
    while True:
        await overlord.run()
    # print(f"{months} months took {round(time.time()-now, 3)}")


async def iterate_forever_and_start_reading_chat(overlord: Overlord):
    asyncio.create_task(overlord.api.start_read_chat())
    await iterate_forever(overlord)
    o.api.send_chat_message("")
    await asyncio.sleep(60 * 60 * 365 * 100)

if __name__ == '__main__':
    o = Overlord()
    # print(", ".join(o.api.commands))
    start(iterate_forever_and_start_reading_chat(o), o)
    # session = database.Session()
    # user = session.query(User).get(1)
    # print(user.points(o.api))
    # print(o.api.subtract_points(user.name, -1))
    # print(user.points(o.api))

    # o.delete_all()
    # start(o.api.start_read_chat(), o)
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









