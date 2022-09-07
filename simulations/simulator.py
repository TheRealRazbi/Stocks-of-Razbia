__all__ = ('FakeAPI', 'Simulator')

from loguru import logger
from sqlalchemy import create_engine

import database
from database import Company, User
from overlord import Overlord

from .user import *
from .fake_api import FakeAPI


class Simulator:
    def __init__(self):
        """This module provides an interface for the class Watch to check the results given X parameters"""
        self.engine = create_engine('sqlite:///:memory:')
        database.Session.configure(bind=self.engine)
        database.Base.metadata.bind = self.engine
        database.Base.metadata.create_all()
        self.session = database.Session()
        self.o = Overlord()
        self.o.api = FakeAPI(overlord=self.o)
        self.spawned_companies_counter = 0  # how many times in the simulator's lifetime, companies have been spawned

    async def spawn_companies_until_max(self):
        while self.o.max_companies > self.session.query(Company).count():
            await self.spawn_companies_once()

    async def spawn_companies_once(self):
        companies_before_spawn = self.session.query(Company).count()
        await self.o.spawn_companies(self.session)
        companies_after_spawn = self.session.query(Company).count()
        how_many_spawned = companies_after_spawn - companies_before_spawn
        self.spawned_companies_counter += how_many_spawned
        if how_many_spawned:
            logger.debug(f"Spawned {how_many_spawned} companies")

    async def pass_month(self):
        await self.o.iterate_companies(self.session)
        await self.spawn_companies_once()
        await self.o.clear_bankrupt(self.session)
        # await self.o.display_update(self.session)
        self.o.months += 1

    async def run(self):
        """Don't use this method for monitoring. Use the class Watch instead"""
        # await self.spawn_companies_until_max()
        #
        # for _ in range(self.YEARS_TO_SIMULATE * 12):
        #     await self.o.iterate_companies(self.session)
        #     await self.o.clear_bankrupt(self.session)
        #
        # for index_company, company in enumerate(self.session.query(Company).all()):
        #     logger.info(company)
        #
        # await self.delete_everything()

    async def clear_database(self):
        database.Base.metadata.drop_all()
        database.Base.metadata.create_all()
        self.session = database.Session()

    def create_user(self, user_type: BaseUser.__class__) -> BaseUser:
        username = generate_random_user_name()
        user_db = User(name=username)
        self.session.add(user_db)
        self.session.commit()
        return user_type(simulator=self, db_user=user_db)
