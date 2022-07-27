import asyncio

from sqlalchemy import create_engine

import database
from database import Company
from overlord import Overlord

import matplotlib.pyplot as plt  # matplotlib is just for plotting stuff, no need to install if you don't use this file

YEARS_TO_SIMULATE = 10


async def main():
    engine = create_engine('sqlite:///:memory:')
    database.Session.configure(bind=engine)
    database.Base.metadata.bind = engine
    database.Base.metadata.create_all()
    session = database.Session()
    o = Overlord()
    o.spawn_companies(session)
    o.spawn_companies(session)
    o.spawn_companies(session)
    o.spawn_companies(session)

    fig, ax = plt.subplots()

    for _ in range(YEARS_TO_SIMULATE * 12):
        await o.iterate_companies(session)
        await o.clear_bankrupt(session)

    for index_company, company in enumerate(session.query(Company).all()):
        print(company)


if __name__ == '__main__':
    asyncio.run(main())
