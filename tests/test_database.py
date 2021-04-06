import aiounittest
from sqlalchemy import create_engine

import database


class AbstractAsyncTestDatabase(aiounittest.AsyncTestCase):
    def setUp(self) -> None:
        engine = create_engine('sqlite:///:memory:')
        database.Session.configure(bind=engine)
        database.Base.metadata.bind = engine
        database.Base.metadata.create_all()
        self.session = database.Session()

