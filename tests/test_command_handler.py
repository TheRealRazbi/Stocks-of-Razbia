import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import commands.exc
from commands import Command, ProperArgumentNotProvided
from multi_arg import Percent, StocksStr, AllStr
from database import Company, User
from test_utils import create_test_database, create_fake_user_context, create_fake_discord_message
from typing import Optional
import itertools


class TestCommand(TestCase):
    def setUp(self) -> None:
        self.session = create_test_database()
        self.user = User(id=163, name='RazbiTh3Player', discord_id='123')
        self.company = Company.create(starting_price=1, name=('RZBI', "Razbi's Bot Solutions"))
        self.session.add(self.company)
        self.session.add(self.user)
        self.session.commit()
        self.ctx = create_fake_user_context(user=self.user, session=self.session)

    def test_basic_command(self):
        def return_number(ctx, number: int):
            return number

        c = Command(func=return_number)
        number = 5
        self.assertEqual(number, c(self.ctx, f'{number}'))

    def test_company_command(self):
        def return_company(ctx, company: Company):
            return company

        c = Command(func=return_company)
        self.assertEqual(self.company, c(self.ctx, f'{self.company.abbv}'))

    def test_multiple_converters_success(self):
        def return_number_or_company(ctx, arg: [Company, int]):
            return arg

        c = Command(func=return_number_or_company)
        number = 5
        self.assertEqual(number, c(self.ctx, f'{number}'))
        self.assertEqual(self.company, c(self.ctx, f'{self.company.abbv}'))

    def test_multiple_converters_failure(self):
        def return_number_or_company(ctx, arg: [Company, int]):
            return arg

        c = Command(func=return_number_or_company)
        number = 5
        self.assertEqual(number, c(self.ctx, f'{number}'))
        wrong_argument = '50%'
        with self.assertRaises(ProperArgumentNotProvided) as cm:
            c(self.ctx, wrong_argument)
            self.assertEqual(cm.exception.arg_name, wrong_argument)

    def test_optional_arguments(self):
        def return_company_and_number(ctx, company: Company, number: Optional[int] = None):
            if number:
                return company, number
            return company

        c = Command(func=return_company_and_number)
        self.assertEqual(self.company, c(self.ctx, f'{self.company.abbv}'))
        number_ = 5
        self.assertEqual((self.company, number_), c(self.ctx, f'{self.company.abbv}', f'{number_}'))

        def return_number_and_company(ctx, number: int, company: Optional[Company] = None):
            if company:
                return number, company
            return number

        c = Command(func=return_number_and_company)
        number_ = 5
        self.assertEqual(number_, c(self.ctx, f'{number_}'))
        self.assertEqual((number_, self.company), c(self.ctx, f'{number_}', f'{self.company.abbv}'))

    def test_user_command_success(self):
        def return_user(ctx, user: User):
            return user

        c = Command(func=return_user)
        discord_message = create_fake_discord_message()
        mention = MagicMock()
        mention.id = 123
        discord_message.mentions = [mention]
        self.ctx.discord_message = discord_message
        self.assertEqual(self.user, c(self.ctx, 'RazbiTh3Player'))

    def test_user_command_failure(self):
        def return_user(ctx, user: User):
            return user

        c = Command(func=return_user)
        with self.assertRaises(commands.exc.ConversionError) as cm:
            c(self.ctx, 'RazbiTh3Player')
            self.assertEqual(cm.exception.msg, 'Command works only on discord.')

    def test_multiple_converters_for_one_argument(self):
        def return_number_or_company(ctx, arg: [Company, int]):
            return arg

        c = Command(func=return_number_or_company)
        number = 5
        self.assertEqual(number, c(self.ctx, f'{number}'))
        self.assertEqual(self.company, c(self.ctx, f'{self.company.abbv}'))

    def test_unordered_args(self):
        def return_number_and_company(ctx, number: int, company: Company, percent: Percent):
            return number, company, percent

        c = Command(func=return_number_and_company, unordered_args=True)
        number_ = 5

        for arg1, arg2, arg3 in itertools.permutations([f'{number_}', f'{self.company.abbv}', '50%']):
            self.assertEqual((number_, self.company, 0.5), c(self.ctx, f'{arg1}', f'{arg2}', f'{arg3}'))

    def test_buy_unordered_args(self):
        def buy(ctx, amount: [int, Percent], company: Company, stocks: Optional[StocksStr] = None):
            if stocks:
                return company, amount, stocks
            return company, amount

        c = Command(func=buy, unordered_args=True)
        self.try_all_permutations(c, [self.company.abbv, '5'], (self.company, 5))
        self.try_all_permutations(c, [self.company.abbv, '5', 'shares'], (self.company, 5, 'shares'))
        self.try_all_permutations(c, [self.company.abbv, '5', 'stocks'], (self.company, 5, 'stocks'))

    def test_buy_unordered_args_and_sequence_arg(self):
        def buy(ctx, amount: [int, Percent], company: [Company], stocks: Optional[StocksStr] = None):
            company_dict = {company.abbv: company for company in company}
            if stocks:
                return company_dict, amount, stocks
            return company_dict, amount

        company2 = Company.create(starting_price=1, name=('TAVR', "Nerzul's Tavern"))
        company3 = Company.create(starting_price=1, name=('WRTR', "Dragormir's Writers"))
        self.session.add(company2)
        self.session.add(company3)
        self.session.commit()

        c = Command(func=buy, unordered_args=True, sequence_arg='company')
        self.try_all_permutations(c, [self.company.abbv, '5'], ({self.company.abbv: self.company}, 5))
        self.try_all_permutations(c,
                                  input_args=[self.company.abbv, '5', 'shares'],
                                  output_args=({self.company.abbv: self.company}, 5, 'shares'))

        self.try_all_permutations(c,
                                  input_args=[self.company.abbv, '5', 'shares', company2.abbv, company3.abbv],
                                  output_args=({self.company.abbv: self.company, company2.abbv: company2,
                                                company3.abbv: company3}, 5, 'shares'))

    def test_buy_improper_argument(self):
        def buy(ctx, company: Company, amount: [int, AllStr]):
            return company, amount

        c = Command(func=buy, unordered_args=False)

        print(c(self.ctx, 'rzbi', '4'))

    def try_all_permutations(self, func, input_args, output_args):
        for arg_group in itertools.permutations(input_args):
            self.assertEqual(output_args, func(self.ctx, *arg_group))


if __name__ == '__main__':
    unittest.main()
