__all__ = (
    'BaseUser', 'IdleUser', 'generate_random_user_name', 'BuyRandomlyWithAllPointsUser', 'InvestOnlyInNewCompanies',
    'PerfectionistEventSeekerUser')

import abc
import random

from database import User, Company
from loguru import logger


class BaseUser(abc.ABC):
    HOURS_A_DAY = 24
    STRATEGY_NAME = 'Nothing'

    def __init__(self, simulator, db_user: User):
        self.s = simulator
        self.db_user = db_user
        self.last_checked_points = -1
        self.last_checked_worth = -1

    async def action_per_month(self) -> None:
        raise NotImplemented

    @property
    async def points(self) -> int:
        points = await self.db_user.points(self.s.o.api, self.s.session)
        self.last_checked_points = points
        return points

    @property
    async def total_worth(self) -> int:
        worth = await self.db_user.total_worth(self.s.o.api, self.s.session)
        self.last_checked_worth = worth
        return worth

    @property
    def name(self) -> str:
        return f"{self.db_user.name}[{self.db_user.id}|{self.STRATEGY_NAME}]"

    async def run_command(self, command: str) -> None:
        # from .simulator import Simulator
        # from .fake_api import FakeAPI
        # self.s: Simulator
        # self.s.o.api: FakeAPI

        await self.s.o.api.run_command(user=self, session=self.s.session, text_without_prefix=command,
                                       discord_message='something')

    def __str__(self):
        # return f'{self.name} - {self.last_checked_points} last checked points - {self.last_checked_worth} last worth checked'
        return f'{self.name}'

    @property
    def irl_hour(self):
        return self.s.o.months * 10 / 60 % 24

    @property
    def is_active(self):
        return self.irl_hour < self.HOURS_A_DAY + 0.0001

    def get_all_companies(self):
        return self.s.session.query(Company).all()


class IdleUser(BaseUser):
    async def action_per_month(self) -> None:
        logger.info(f"{self.name} has {await self.points} points and won't do anything with them")


class BuyRandomlyWithAllPointsUser(BaseUser):
    CHANCE_TO_BUY = 50
    HOURS_A_DAY = 2
    STRATEGY_NAME = 'I buy randomly all-in'

    async def action_per_month(self) -> None:
        if not self.is_active:
            logger.debug(f"Sleeping at {self.irl_hour:.2f} | user: {self}")
            return

        if random.randint(1, 100) < self.CHANCE_TO_BUY:
            logger.info(f"Investing at {self.irl_hour:.2f} | user: {self}")
            await self.run_command('autoinvest all')
        # logger.info(f"{self.name} has {await self.points} points and won't do anything with them")


class PerfectionistEventSeekerUser(BaseUser):
    HOURS_A_DAY = 4
    STRATEGY_NAME = 'I buy only from events'

    def __init__(self, simulator, db_user: User):
        super(PerfectionistEventSeekerUser, self).__init__(simulator, db_user)
        self.companies_last_month = []

    async def action_per_month(self) -> None:
        if not self.is_active:
            return
        companies_this_month = self.s.session.query(Company).filter(Company.event_months_remaining != 0)
        if self.companies_last_month:
            for company in companies_this_month:
                if company not in self.companies_last_month:
                    await self.run_command(f'buy {company.abbv} all')
                    logger.info(f"Bought {company.abbv} with all my stocks | user: {self}")
                    break
                else:
                    logger.debug(f"Company {company.abbv} not on event")

        self.companies_last_month = companies_this_month


class InvestOnlyInNewCompanies(BaseUser):
    HOURS_A_DAY = 8
    STRATEGY_NAME = 'Invest only in new companies'

    def __init__(self, simulator, db_user: User):
        super(InvestOnlyInNewCompanies, self).__init__(simulator, db_user)
        self.companies_last_month = []

    async def action_per_month(self) -> None:
        if not self.is_active:
            return

        companies_this_month = self.get_all_companies()
        if self.companies_last_month:
            for company in companies_this_month:
                if company not in self.companies_last_month:
                    await self.run_command(f'buy {company.abbv} all')
                    logger.info(f"Bought {company.abbv} with all my stocks | user: {self}")
                    break
                else:
                    logger.debug(f"Company {company.abbv} not new")

        self.companies_last_month = companies_this_month


def generate_random_user_name():
    return random.choice(('Razbi', 'Croan', 'Swavy', 'L_d_Best', 'Hoppolino', 'Frog'))
