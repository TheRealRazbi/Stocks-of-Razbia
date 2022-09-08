__all__ = ['create_test_database', 'create_fake_user_context', 'create_fake_discord_message', 'create_async_test_database']

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session as SessionType
from contexts import UserContext

import database


def create_test_database() -> SessionType:
    engine = create_engine('sqlite:///:memory:')
    database.Session.configure(bind=engine)
    database.Base.metadata.bind = engine
    database.Base.metadata.create_all()
    return database.Session()


async def create_async_test_database() -> database.AsyncSession:
    engine = create_engine('sqlite:///:memory:')
    async_engine = create_async_engine('sqlite+aiosqlite:///:memory:')

    database.Session.configure(bind=engine)
    database.AsyncSession.configure(bind=async_engine)
    database.Base.metadata.bind = async_engine
    async with async_engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
    return database.AsyncSession()


def create_test_send_message():
    def send_message(**kwargs):
        print(kwargs)

    return send_message


def create_fake_discord_message():
    class FakeDiscordMessage:
        pass

    return FakeDiscordMessage


def create_fake_user_context(**kwargs):
    ctx = UserContext(
        user=kwargs.get('user', None),
        api=kwargs.get('api', None),
        session=kwargs.get('session', None),
        discord_message=kwargs.get('discord_message', None),
        send_message=kwargs.get('send_message', create_test_send_message()),
    )
    return ctx


def main():
    pass


if __name__ == '__main__':
    main()
