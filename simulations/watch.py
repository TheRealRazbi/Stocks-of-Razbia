__all__ = ('Watch',)

import math
from typing import List

from loguru import logger

from .simulator import Simulator
from .user import *


class Watch:
    """
    Let's you monitor the simulator
    """

    def __init__(self):
        self.s: Simulator = Simulator()
        self.IRL_DAYS_TO_SIMULATE = 7
        self.YEARS_TO_SIMULATE = self.IRL_DAYS_TO_SIMULATE * 12
        self.SIMULATE_N_TIMES = 3
        self.total_spawned_companies = 0
        self.users: List[BaseUser] = []
        self.constant_buy_user: [BuyRandomlyWithAllPointsUser, None] = None
        self.user_performances = {}

    async def run(self):
        for simulation in range(self.SIMULATE_N_TIMES):
            await self.before_simulation()
            for month in range(self.months_to_simulate):
                logger.info(f"Simulation {simulation} | {self.s.o.year_and_month}")
                await self.pass_month()
            await self.reset_simulator_and_save_info(simulation)
        await self.after_simulations_info()

    async def pass_month(self):
        await self.s.pass_month()
        for user in self.users:
            await user.action_per_month()

    async def before_simulation(self):
        self.create_user(InvestOnlyInNewCompanies)
        self.create_user(BuyRandomlyWithAllPointsUser)
        self.create_user(PerfectionistEventSeekerUser)

    async def reset_simulator_and_save_info(self, simulation_count: int):
        self.total_spawned_companies += self.s.spawned_companies_counter
        self.user_performances[simulation_count] = {user.name: await user.total_worth for user in self.users}
        await self.reset_simulator()

    async def reset_simulator(self):
        await self.s.clear_database()
        self.users = []
        self.s = Simulator()
        logger.debug("Simulator has been reset.")

    async def after_simulations_info(self):
        # logger.info(f"Spawned Companies In Total: {self.total_spawned_companies}")
        logger.info(f"Spawned Companies Avg Per Simulation: {self.total_spawned_companies / self.SIMULATE_N_TIMES:.2f}")
        bankrupt_companies_total = self.total_spawned_companies - self.s.o.max_companies * self.SIMULATE_N_TIMES
        bankrupt_companies_avg_per_simulation = bankrupt_companies_total / self.SIMULATE_N_TIMES
        logger.info(f"Bankrupt Companies Avg Per Simulation: {bankrupt_companies_avg_per_simulation:.2f}")
        logger.info(
            f'Bankrupt Companies Avg Per Month: {bankrupt_companies_avg_per_simulation / self.months_to_simulate:.2f}')
        for simulation in self.user_performances.keys():
            for user, amount in self.user_performances[simulation].items():
                logger.info(f'Simulation {simulation}: {user}: {amount:_}')

    @property
    def months_to_simulate(self):
        return math.floor(self.YEARS_TO_SIMULATE * 12)

    def create_user(self, user_type: BaseUser.__class__):
        user = self.s.create_user(user_type)
        self.users.append(user)
        return user
