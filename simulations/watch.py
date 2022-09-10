__all__ = ('Watch',)

import math
from typing import List

from loguru import logger

import database
from .simulator import Simulator
from .user import *
import configparser


class Watch:
    """
    Lets you monitor the simulator
    """

    def __init__(self):
        self.VERSION = 0  # bump this version each balance change
        self.IRL_DAYS_TO_SIMULATE = 7
        self.YEARS_TO_SIMULATE = self.IRL_DAYS_TO_SIMULATE * 12
        self.SIMULATE_N_TIMES = 999_999_999_999
        self.USER_ALGORITHMS = (
            InvestOnlyInNewCompanies, BuyRandomlyWithAllPointsUser, PerfectionistEventSeekerUser, InvestInTop3Companies,
            InvestInAllCompaniesConstantlyEqually,
        )

        self.s: [Simulator, None] = None
        self.total_spawned_companies = 0
        self.users: List[BaseUser] = []
        self.constant_buy_user: [BuyRandomlyWithAllPointsUser, None] = None
        self.user_performances = {}
        self.simulations_so_far = 1  # 1 instead of 0 so the self.save() doesn't divide by 0
        self.save_load_config = configparser.ConfigParser()
        # self.user_session = database.AsyncSession()

    async def setup_simulator(self) -> None:
        self.s = Simulator()
        await self.s.configure_database()

    @property
    def config_section_name(self):
        return f'{self.IRL_DAYS_TO_SIMULATE}_{"|".join(user.STRATEGY_NAME for user in self.USER_ALGORITHMS)}'

    async def load(self):
        self.save_load_config.read(f'simulation-data/{self.VERSION}.ini')
        if self.config_section_name in self.save_load_config:
            existing = self.save_load_config[self.config_section_name]
            self.simulations_so_far = existing.getint('simulations', 1)

    async def save(self, simulation_count):
        if self.config_section_name not in self.save_load_config:
            self.save_load_config[self.config_section_name] = {}
        existing = self.save_load_config[self.config_section_name]
        existing['simulations'] = str(1 + existing.getint('simulations', 1))
        for user in self.users:
            old_net_worth = existing.getfloat(user.strategy_and_hours, 0)
            net_worth_this_time = self.user_performances[simulation_count][user.name]
            new_net_worth = old_net_worth + ((net_worth_this_time-old_net_worth)//simulation_count)
            existing[user.strategy_and_hours] = str(new_net_worth)

        with open(f'simulation-data/{self.VERSION}.ini', "w") as configfile:
            self.save_load_config.write(configfile)

    async def run(self):
        await self.load()
        await self.setup_simulator()
        for simulation in range(self.simulations_so_far, self.simulations_so_far+self.SIMULATE_N_TIMES):
            await self.before_simulation()
            for month in range(self.months_to_simulate):
                logger.info(f"Simulation {simulation} | {self.s.o.year_and_month}")
                await self.pass_month()
            await self.reset_simulator_and_save_info(simulation)
        await self.after_all_simulations()

    async def pass_month(self):
        await self.s.pass_month()
        for user in self.users:
            await user.action_per_month()

    async def before_simulation(self):
        # self.user_session = database.AsyncSession()
        for user_algorithm in self.USER_ALGORITHMS:
            await self.create_user(user_algorithm, session=self.s.session)

    async def reset_simulator_and_save_info(self, simulation_count: int):
        self.total_spawned_companies += self.s.spawned_companies_counter
        self.user_performances[simulation_count] = {user.name: await user.total_worth for user in self.users}
        await self.save(simulation_count)
        await self.reset_simulator()

    async def reset_simulator(self):
        await self.user_session.close()
        await self.s.clear_database()
        self.users = []
        await self.setup_simulator()
        logger.debug("Simulator has been reset.")

    async def after_all_simulations(self):
        # logger.info(f"Spawned Companies In Total: {self.total_spawned_companies}")
        logger.add(f'simulation-data/results.log')
        logger.info(f'{self.IRL_DAYS_TO_SIMULATE=}, {self.SIMULATE_N_TIMES=}, {self.simulations_so_far=}')
        logger.info(f"Spawned Companies Avg Per Simulation: {self.total_spawned_companies / self.SIMULATE_N_TIMES:.2f}")
        bankrupt_companies_total = self.total_spawned_companies - self.s.o.max_companies * self.SIMULATE_N_TIMES
        bankrupt_companies_avg_per_simulation = bankrupt_companies_total / self.SIMULATE_N_TIMES
        logger.info(f"Bankrupt Companies Avg Per Simulation: {bankrupt_companies_avg_per_simulation:.2f}")
        logger.info(
            f'Bankrupt Companies Avg Per Month: {bankrupt_companies_avg_per_simulation / self.months_to_simulate:.2f}')
        first_user_performance_key = list(self.user_performances.keys())[0]
        avg_user_performance = {user: 0 for user in self.user_performances[first_user_performance_key]}  # get their name
        for simulation in self.user_performances.keys():
            for user, amount in self.user_performances[simulation].items():
                logger.info(f'Simulation {simulation}: {user}: {amount:_} net worth')
                avg_user_performance[user] += amount
        for user, amount in avg_user_performance.items():
            logger.info(f"Strategy {user}: {amount // self.SIMULATE_N_TIMES:_} average net worth")
        logger.info("###########################################################################")

    @property
    def months_to_simulate(self):
        return math.floor(self.YEARS_TO_SIMULATE * 12)

    async def create_user(self, user_type: BaseUser.__class__, session=database.AsyncSession):
        users = await self.s.create_user(user_type, session=session)
        self.users += users
        return users
