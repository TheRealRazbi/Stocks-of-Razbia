import unittest
from unittest import TestCase

from contexts import UserContext
from commands.converters import PercentConverter, CompanyConverter
from commands.cmd_utils import order_and_convert_args
from commands.exc import ProperArgumentNotProvided
import database
from tests.test_utils import create_test_database


class TestOrderArgs(TestCase):
    def setUp(self) -> None:
        self.session = create_test_database()
        self.ctx = UserContext(user=None, session=self.session, api=None, send_message=None, discord_message=None)
        self.company = database.Company(abbv='RZBI', full_name="Razbi's Company")
        self.session.add(self.company)
        self.session.commit()

    def test_with_company_and_percent_converters(self):
        args = ["RZBI", "80%"]
        needed_args = {'company': CompanyConverter, 'amount': PercentConverter}
        res = order_and_convert_args(self.ctx, needed_args=needed_args, raw_args=args)
        desired_output = {'company': self.company, 'amount': .8}
        self.assertEqual(res, desired_output)

    def test_not_enough_args_and_error_message(self):
        args = ["RZBI"]
        needed_args = {'company': CompanyConverter, 'amount': PercentConverter}
        with self.assertRaises(expected_exception=ProperArgumentNotProvided) as cm:
            order_and_convert_args(self.ctx, needed_args=needed_args, raw_args=args)
        self.assertEqual(cm.exception.msg, f"Invalid 'amount' or not provided")


if __name__ == '__main__':
    unittest.main()
