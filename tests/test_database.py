import aiounittest

from tests.test_utils import create_test_database


class AbstractAsyncTestDatabase(aiounittest.AsyncTestCase):
    def setUp(self) -> None:
        self.session = create_test_database()
