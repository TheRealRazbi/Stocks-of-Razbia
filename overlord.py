import json
import time
import random

import sqlalchemy as sql

from API import API
import asyncio
from bot_commands import register_commands
from database import User, Company
import database
import custom_tools
from termcolor import colored
import math
import os
import config_server
import config_server.forms
from company_names import load_default_names
import webbrowser
from more_tools import CachedProperty


class Overlord:
    def __init__(self, loop=None):
        database.Base.metadata.create_all()
        session = database.Session()
        self.last_check = 0
        self.loop = loop
        if loop is None:
            self.loop = asyncio.get_event_loop()
        self.api = API(overlord=self, loop=loop)
        register_commands(self.api)
        self.iterate_cooldown = 10*60
        # self.iterate_cooldown = 3
        self.new_companies_messages = ['ughhh... buy from them or smth?', "stonks", "nice, I guess...", "oh yeah, I like that one",
                                       "wait, what are these?", "I like turtles", "who's Razbi?", "Glory to Arstotzka, wait..., wrong game", "buy buy buy"]
        self.bankrupt_companies_messages = ['Feelsbadman', 'just invest better Kappa', 'imagine losing {currency_name} to those Kappa', 'this is fine monkaS']
        self.max_companies = 7
        self.spawn_ranges = {
            "poor_range": (7, 15),
            "expensive_range": (15, 35),
        }
        self._cache = {}

        self.stock_increase = []
        self.bankrupt_info = []
        self.owners_of_bankrupt_companies = set()

        self.names = {}
        self.load_names()

        self.rich = 0
        self.poor = 0
        self.load_rich_poor()

        self.months = 0
        self.load_age(session=session)
        self.started = False
        session.close()

    async def run(self):
        time_since_last_run = time.time() - self.last_check
        if self.started and time_since_last_run > self.iterate_cooldown:
            self.last_check = time.time()
            session = database.Session()

            await self.iterate_companies(session)
            self.spawn_companies(session)
            await self.clear_bankrupt(session)

            self.display_update()
            self.months += 1
            self.update_age(session)
            session.close()
        else:
            await asyncio.sleep(3)
            # time.sleep(self.iterate_cooldown-time_since_last_run)

    def spawn_companies(self, session: database.Session):
        companies_to_spawn = 0
        spawned_companies = []
        if session.query(Company).count() < self.max_companies:
            companies_to_spawn = self.max_companies - session.query(Company).count()
            if companies_to_spawn > 2:
                companies_to_spawn = 2
        if session.query(Company).count() == 0 and companies_to_spawn == 2:
            print(colored("hint: you can type the commands only in your twitch chat", "green"))
            self.api.send_chat_message(f"Welcome to Stocks of Razbia. "
                                       "Use '!stocks' to see basic available commands. Remember: company_abbreviation[current_price, price_change] "
                                       "tip: you don't have to type company names in caps. ")

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
            spawned_companies.append(f"[{company.abbv}] {company.full_name}, stock_price: {company.stock_price:.1f} {self.currency_name}")
        if spawned_companies:
            tip = random.choice(self.new_companies_messages)
            self.api.send_chat_message(f"Newly spawned companies: {' | '.join(spawned_companies)}, {tip}")

        session.commit()

    async def iterate_companies(self, session: database.Session):
        for index_company, company in enumerate(session.query(Company).all()):
            res = company.iterate()
            if res:
                # stock_increase = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}"\
                #                  f"{'+' if company.price_diff >= 0 else ''}{company.price_diff}]"
                # self.stock_increase.append(stock_increase)
                self.stock_increase.append(True)
                shares = session.query(database.Shares).filter_by(company_id=company.id)
                for share in shares:
                    cost = math.ceil(math.ceil(share.amount*company.stock_price)*.1)
                    user = session.query(User).get(share.user_id)
                    await self.api.upgraded_add_points(user, cost, session)

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

    async def clear_bankrupt(self, session: database.Session):
        for index_company, company in enumerate(session.query(Company).filter_by(bankrupt=True)):
            self.bankrupt_info.append(f'{company.abbv.upper()}')
            shares = session.query(database.Shares).filter_by(company_id=company.id).all()
            for share in shares:
                user = session.query(database.User).get(share.user_id)
                await self.api.upgraded_add_points(user, share.amount, session)
                self.owners_of_bankrupt_companies.add(f'@{user.name}')
                # print(f"Refunded {share.amount} points to @{user.name}")
            session.delete(company)
            session.commit()

    def load_names(self, session: database.Session = None):
        if session is None:
            session = database.Session()
        companies = session.query(Company).all()
        company_names_db = session.query(database.Settings).get('company_names')
        if company_names_db:
            self.names = {item["abbv"]: item["company_name"] for item in json.loads(company_names_db.value)}
        else:
            self.names = {item["abbv"]: item["company_name"] for item in load_default_names()}
            session.add(database.Settings(key='company_names', value=json.dumps(load_default_names())))
            session.commit()
        for company in companies:
            self.names.pop(company.abbv, None)

        session.commit()

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

    def load_age(self, session: database.Session):
        age = session.query(database.Settings).get('age')
        if age is None:
            if os.path.exists('lib/age'):
                with open('lib/age', "r") as f:
                    age = f.read()
                session.add(database.Settings(key='age', value=age))
                session.commit()
                os.remove('lib/age')
            else:
                session.add(database.Settings(key='age', value='0'))
                session.commit()
                age = 0
        else:
            age = age.value

        self.months = int(age)

    def update_age(self, session: database.Session):
        age = session.query(database.Settings).get('age')
        age.value = str(self.months)
        session.commit()

    def display_update(self):
        if self.stock_increase:
            # companies_to_announce, owners = self.get_companies_for_updates(session)
            # self.api.send_chat_message(f'Month: {self.months} | {", ".join(self.stock_increase)}')

            # self.api.send_chat_message(f'Year: {int(self.months/12)} | Month: {self.months%12} | '
            #                            f'{", ".join(companies_to_announce)} {" ".join(owners)} | '
            #                            f'Use "!stocks" to display all available commands.')

            # self.api.send_chat_message(f"Minigame basic commands: !introduction, !companies, !my shares, !buy, !all commands, !stocks")

            self.stock_increase = []
        # self.api.send_chat_message(f"Companies: {session.query(Company).count()}/{self.max_companies} Rich: {self.rich}"
        #                            f", Poor: {self.poor}, Most Expensive Company: {self.most_expensive_company(session)}")
        if self.bankrupt_info:
            random_comment = random.choice(self.bankrupt_companies_messages).format(currency_name=self.currency_name)
            self.api.send_chat_message(f'The following companies bankrupt: {", ".join(self.bankrupt_info)} '
                                       f'{" ".join(self.owners_of_bankrupt_companies)} {random_comment if self.owners_of_bankrupt_companies else ""}')
            self.bankrupt_info = []

    async def start_periodic_announcement(self):
        while True:
            if self.started:
                stonks_or_stocks = random.choice(['stocks', 'stonks'])
                final_message = random.choice([f'Wanna make some {self.currency_name} through stonks?', 'Be the master of stonks'])+' '

                main_variation = random.randint(1, 2)
                if main_variation == 1:
                    command_order = ['!introduction', '!companies', '!buy', f'!{stonks_or_stocks}', '!autoinvest', '!my income']
                    random.shuffle(command_order)
                    help_tip = random.choice(['Here are some commands to help you do that', "Ughh maybe through these?",
                                              "I wonder what are these for", "Commands", "Turtles"])
                    final_message += f"{help_tip}: {', '.join(command_order)}"
                elif main_variation == 2:
                    final_message += "For newcomers we got: '!autoinvest <budget>'"
                elif main_variation == 3:
                    pass
                self.api.send_chat_message(final_message)
                await asyncio.sleep(60 * 30)
            else:
                await asyncio.sleep(.5)

    @staticmethod
    def get_companies_for_updates(session: database.Session):
        res = []
        owners = session.query(database.User).filter(database.User.shares).all()
        owners = [f'@{user.name}' for user in owners]

        for company in session.query(Company).filter(Company.shares).all():
            if len(res) >= 5:
                break
            if company.price_diff == 0:
                continue
            # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
            message = company.announcement_description
            res.append(message)

        if len(res) < 3:
            richest_companies = session.query(database.Company).order_by(Company.stock_price.desc()).limit(3-len(res)).all()
            for company in richest_companies:
                if company.price_diff == 0:
                    continue
                # message = f"{company.abbv.upper()}[{company.stock_price - company.price_diff:.1f}{company.price_diff:+}]"
                # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
                message = company.announcement_description
                if company.stock_price < 0:
                    print("A company has like stock_price under 0, I have absolutely no idea how was this possible, please tell Razbi about it")
                if message not in res:
                    res.append(message)
        return res, owners

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

    @CachedProperty
    def currency_name(self):
        session = database.Session()
        if currency_name := session.query(database.Settings).get('currency_name'):
            currency_name = currency_name.value
            # self._cache['currency_name'] = currency_name
        else:
            currency_name = 'points'
            session.add(database.Settings(key='currency_name', value=currency_name))
            session.commit()
        return currency_name

    def mark_dirty(self, setting):
        if setting in self._cache:
            del self._cache[setting]

    @staticmethod
    def display_credits():
        print(f"""
--------------------------------------------------------------------------
Welcome to {colored('Stocks of Razbia', 'green')}
This program is open-source and you can read the code at {colored('https://github.com/TheRealRazbi/Stocks-of-Razbia', 'yellow')}
In fact you can even read the code by opening {colored('lib/code/', 'green')}
ALL the minigame files are stored in the same folder as the executable, in the {colored('lib/', 'green')}
You can check for updates when you start the program and pick the other option.
This program was made by {colored('Razbi', 'magenta')} and {colored('Nesami', 'magenta')}
Program started at {colored(str(time.strftime('%H : %M')), 'cyan')}
--------------------------------------------------------------------------\n
        """)


def start(func, overlord: Overlord):
    return overlord.loop.run_until_complete(func)


async def iterate_forever(overlord: Overlord):
    while True:
        await overlord.run()


async def iterate_forever_and_start_reading_chat(overlord: Overlord):
    asyncio.create_task(overlord.api.start_read_chat())
    await iterate_forever(overlord)
    o.api.send_chat_message("")
    await asyncio.sleep(60 * 60 * 365 * 100)


async def iterate_forever_read_chat_and_run_interface(overlord: Overlord):
    webbrowser.open('http://localhost:5000')
    config_server.app.overlord = overlord
    await asyncio.gather(
        config_server.app.run_task(use_reloader=False),
        iterate_forever(overlord),
        overlord.api.start_read_chat(),
        overlord.api.twitch_key_auto_refresher(),
        overlord.start_periodic_announcement(),
        asyncio.sleep(60 * 60 * 365 * 100),
    )

    await asyncio.sleep(60 * 60 * 365 * 100)


if __name__ == '__main__':
    o = Overlord()
    start(iterate_forever_read_chat_and_run_interface(o), o)
    # webbrowser.open('http://localhost:5000')










