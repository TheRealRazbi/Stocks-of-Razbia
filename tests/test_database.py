import asyncio

import aiounittest
from sqlalchemy.sql import select

from database import Company, AsyncSession, User, Shares
from tests.test_utils import create_test_database, create_async_test_database


class AbstractSyncTestDatabase(aiounittest.AsyncTestCase):
    def setUp(self) -> None:
        self.session = create_test_database()


class AbstractAsyncTestDatabase(aiounittest.AsyncTestCase):
    # async def a

    def setUp(self) -> None:
        loop = asyncio.get_event_loop()
        self.session: AsyncSession = loop.run_until_complete(create_async_test_database())

    def tearDown(self) -> None:
        asyncio.get_event_loop().run_until_complete(self.session.close())

    async def add_company(self, short_name: str = 'RZBI', full_name: str = "Razbi's Bot Solutions", stock_price=5,
                          **kwargs) -> Company:
        company = Company(abbv=short_name, full_name=full_name, stock_price=stock_price, **kwargs)
        return await self.add_to_db(company)

    async def add_user(self, name='Razbi', **kwargs) -> User:
        user = User(name=name, **kwargs)
        return await self.add_to_db(user)

    async def add_share(self, user: User, company: Company, amount: int = 1) -> Shares:
        share = Shares(user_id=user.id, company_id=company.id, amount=amount)
        return await self.add_to_db(share)

    async def add_to_db(self, obj):
        self.session.add(obj)
        await self.session.commit()
        return obj


class AsyncTestDatabaseCompany(AbstractAsyncTestDatabase):
    async def test_add_company(self):
        company = await self.add_company()
        query = select(Company)
        res = await self.session.execute(query)
        self.assertEqual(res.scalars().first(), company)

    async def test_check_stocks_bought(self):
        company = await self.add_company()
        stocks_bought = await company.stocks_bought(self.session)  # no stocks bought
        self.assertEqual(stocks_bought, 0)

        user = await self.add_user()
        amount = 500
        await self.add_share(user=user, company=company, amount=amount)

        stocks_bought = await company.stocks_bought(self.session)  # 500 stocks bought by 1 user
        self.assertEqual(stocks_bought, amount)

        user_2 = await self.add_user()
        await self.add_share(user=user_2, company=company, amount=amount // 2)

        stocks_bought = await company.stocks_bought(self.session)  # 750 stocks bought in total by 2 users
        self.assertEqual(stocks_bought, amount + amount // 2)

    async def test_access_all_company_attributes(self):
        company = await self.add_company()

