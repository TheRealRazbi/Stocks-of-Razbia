__all__ = (
    'BaseUser', 'IdleUser', 'generate_random_user_name', 'BuyRandomlyWithAllPointsUser', 'InvestOnlyInNewCompanies',
    'PerfectionistEventSeekerUser', 'InvestInAllCompaniesConstantlyEqually', 'InvestInTop3Companies')

import abc
import random
import time

from loguru import logger
from sqlalchemy import select

import database
from database import User, Company, AsyncSession


class BaseUser(abc.ABC):
    HOURS_A_DAY = 24
    STRATEGY_NAME = 'Nothing'

    def __init__(self, simulator, db_user: User, hours_a_day: int, session: database.AsyncSession):
        self.s = simulator
        self.db_user = db_user
        self.HOURS_A_DAY = hours_a_day
        self.session = session
        self.last_checked_points = -1
        self.last_checked_worth = -1

    async def action_per_month(self) -> None:
        if not self.is_active:
            return
        past = time.perf_counter()
        await self.action()
        logger.debug(f'{self.name} took {time.perf_counter()-past:,.2f} seconds')

    async def action(self) -> None:
        raise NotImplemented

    @property
    async def points(self) -> int:
        points = await self.db_user.points(self.s.o.api, self.session)
        self.last_checked_points = points
        return points

    @property
    async def total_worth(self) -> int:
        worth = await self.db_user.total_worth(self.s.o.api, self.session)
        self.last_checked_worth = worth
        return worth

    @property
    def name(self) -> str:
        # return f"{self.db_user.name}[{self.db_user.id}|{self.STRATEGY_NAME}]"
        return f"[{self.db_user.id}|{self.STRATEGY_NAME}|{self.HOURS_A_DAY}]"

    @property
    def strategy_and_hours(self):
        return f"{self.STRATEGY_NAME}|{self.HOURS_A_DAY}"

    async def run_command(self, command: str) -> None:
        await self.s.o.api.run_command(user=self, session=self.session, text_without_prefix=command,
                                       discord_message='something')

    async def all_in_companies(self, companies, not_in, not_in_message=""):
        for company in companies:
            if company not in not_in:
                await self.run_command(f'buy {company.abbv} all')
                logger.debug(f"Bought {company.abbv} with all my stocks | user: {self}")
                break
            else:
                if not_in_message:
                    logger.debug(not_in_message.format(abbv=company.abbv))

    def __str__(self):
        return f'{self.name}'

    @property
    def irl_hour(self):
        return self.s.o.months * 10 / 60 % 24

    @property
    def is_active(self):
        return self.irl_hour < self.HOURS_A_DAY + 0.0001

    @staticmethod
    def get_all_companies(session: AsyncSession):
        return Company.get_all_companies(session=session)


class IdleUser(BaseUser):
    async def action(self) -> None:
        logger.info(f"{self.name} has {await self.points} points and won't do anything with them")


class BuyRandomlyWithAllPointsUser(BaseUser):
    CHANCE_TO_BUY = 50
    STRATEGY_NAME = 'Buy all-in randomly'

    async def action(self) -> None:
        # if not self.is_active:
        #     logger.debug(f"Sleeping at {self.irl_hour:.2f} | user: {self}")
        #     return

        if random.randint(1, 100) < self.CHANCE_TO_BUY:
            logger.debug(f"Investing at {self.irl_hour:.2f} | user: {self}")
            await self.run_command('autoinvest all')
        # logger.debug(f"{self.name} has {await self.points} points and won't do anything with them")


class PerfectionistEventSeekerUser(BaseUser):
    STRATEGY_NAME = 'Buy only from events'

    def __init__(self, simulator, db_user: User, hours_a_day, session):
        super(PerfectionistEventSeekerUser, self).__init__(simulator, db_user, hours_a_day, session)
        self.companies_last_month = []

    async def action(self) -> None:
        # companies_this_month = self.session.query(Company).filter(Company.event_months_remaining != 0)
        companies_this_month = await Company.get_all_companies(session=self.session,
                                                               filter_=Company.event_months_remaining != 0)

        if self.companies_last_month:
            await self.all_in_companies(companies=companies_this_month, not_in=self.companies_last_month,
                                        not_in_message="Company {abbv} not on event")

        self.companies_last_month = companies_this_month


class InvestOnlyInNewCompanies(BaseUser):
    STRATEGY_NAME = 'Invest only in new companies'

    def __init__(self, simulator, db_user: User, hours_a_day, session):
        super(InvestOnlyInNewCompanies, self).__init__(simulator, db_user, hours_a_day, session)
        self.companies_last_month = []

    async def action(self) -> None:
        companies_this_month = await self.get_all_companies(self.session)
        if self.companies_last_month:
            await self.all_in_companies(companies=companies_this_month, not_in=self.companies_last_month,
                                        not_in_message="Company {abbv} not new")

        self.companies_last_month = companies_this_month


class InvestInTop3Companies(BaseUser):
    STRATEGY_NAME = 'Invest only in top 3 companies'

    def __init__(self, simulator, db_user: User, hours_a_day, session):
        super(InvestInTop3Companies, self).__init__(simulator, db_user, hours_a_day, session)
        self.top_companies_last_month = []

    async def action(self) -> None:
        query = select(Company).order_by(Company.stock_price).limit(3)  # get only top 3 companies

        top_companies_this_month = (await self.session.scalars(query)).all()

        new_top = False
        if self.top_companies_last_month:
            for company in top_companies_this_month:
                if company not in self.top_companies_last_month:
                    new_top = True
                    break

        if new_top:
            await self.run_command('sellall')
            await self.run_command(f'buy all {" ".join(company.abbv for company in top_companies_this_month)}')

        self.top_companies_last_month = top_companies_this_month


class InvestInAllCompaniesConstantlyEqually(BaseUser):
    STRATEGY_NAME = "Invest in all companies equally"

    async def action(self) -> None:
        companies = await self.get_all_companies(session=self.session)
        await self.run_command('sellall')
        await self.run_command(f'buy all {" ".join(company.abbv for company in companies)}')


def generate_random_user_name():
    return random.choice(('Razbi', 'Croan', 'Swavy', 'L_d_Best', 'Hoppolino', 'Frog'))
