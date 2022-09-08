__all__ = ["engine", "Session", "Base", "AsyncSession", "select", "get_object_by_kwargs", "count_from_table"]

from sqlalchemy import create_engine, event, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as AsyncSession_
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker, exc
from sqlalchemy.future import select
import os


def _fk_pragma_on_connect(dbapi_con, con_record):
    """This will enable foreign keys on SQLite"""
    dbapi_con.execute('PRAGMA foreign_keys=ON')


if os.path.exists('db.sqlite'):
    os.replace('db.sqlite', 'lib/db.sqlite')

engine = create_engine('sqlite:///lib/db.sqlite', echo=False)
event.listen(engine, 'connect', _fk_pragma_on_connect)
Session = sessionmaker(bind=engine, expire_on_commit=False)

async_engine = create_async_engine('sqlite+aiosqlite:///lib/db.sqlite', echo=False)
AsyncSession = sessionmaker(bind=async_engine, class_=AsyncSession_, expire_on_commit=False)


@as_declarative(bind=engine)
class Base:
    def __repr__(self) -> str:
        return self._repr(**self._getattrs("id"))

    def _getattrs(self, *attrs: str):
        return {attr: getattr(self, attr) for attr in attrs}

    def _repr(self, **fields) -> str:
        """
        Helper for __repr__
        """
        field_strings = []
        at_least_one_attached_attribute = False
        for key, field in fields.items():
            try:
                field_strings.append(f'{key}={field!r}')
            except exc.DetachedInstanceError:
                field_strings.append(f'{key}=DetachedInstanceError')
            else:
                at_least_one_attached_attribute = True
        if at_least_one_attached_attribute:
            return f"<{self.__class__.__name__}({', '.join(field_strings)})>"
        return f"<{self.__class__.__name__} {id(self)}>"


async def get_object_by_kwargs(table, session: AsyncSession, **kwargs):
    return (await session.scalars(select(table).filter_by(**kwargs))).first()


async def get_all_objects_by_kwargs(table, session: AsyncSession, **kwargs):
    return (await session.scalars(select(table).filter_by(**kwargs))).all()


async def count_from_table(table, session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(table))

