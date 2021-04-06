import aiounittest
from database import Company, User, Shares
from testing_commands import FakeOverlord

from tests.test_database import AbstractAsyncTestDatabase


class TestCommands(AbstractAsyncTestDatabase):
    def setUp(self) -> None:
        super(TestCommands, self).setUp()
        self.user = User(name='razbi')
        self.company = Company.create(starting_price=5, name=['test', 'Dummy Company'])
        self.second_company = Company.create(starting_price=5, name=['s_test', 'Second Dummy Company'])
        self.session.add(self.user)
        self.session.add(self.company)
        self.session.add(self.second_company)
        self.session.commit()
        self.share = Shares(user_id=self.user.id, company_id=self.company.id, amount=100)
        self.session.add(self.share)
        self.session.commit()

        self.overlord = FakeOverlord()

    async def test_passive_income(self):
        self.share.amount = 1_000
        self.assertEqual(self.user.passive_income(company=self.company, session=self.session), 490)
        self.share.amount = 5_000
        self.assertEqual(self.user.passive_income(company=self.company, session=self.session), 2_251)
        self.share.amount = 50_000
        self.assertEqual(self.user.passive_income(company=self.company, session=self.session), 2_500)
        self.share.amount = 500_000
        self.assertEqual(self.user.passive_income(company=self.company, session=self.session), 25_000)
        self.assertEqual(self.user.passive_income(company=self.second_company, session=self.session), 0)

    async def test_buy_command(self):
        await self.overlord.api.handler('!buy test 1')
        print("\n".join(self.overlord.return_sent_messages()))

    async def test_for_development(self):
        # self.share.amount = 500_000
        # print(self.user.passive_income(company=self.company, session=self.session))
        # self.session.delete(self.share)
        # self.session.commit()
        print(self.user.passive_income(company=self.company, session=self.session))


if __name__ == '__main__':
    aiounittest.async_test()
