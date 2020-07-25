__all__ = ["engine", "Session", "Base"]

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker, exc
import os


def _fk_pragma_on_connect(dbapi_con, con_record):
    """This will enable foreign keys on SQLite"""
    dbapi_con.execute('PRAGMA foreign_keys=ON')


if os.path.exists('db.sqlite'):
    os.replace('db.sqlite', 'lib/db.sqlite')


engine = create_engine('sqlite:///lib/db.sqlite', echo=False)
event.listen(engine, 'connect', _fk_pragma_on_connect)
Session = sessionmaker(bind=engine)


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
            return f"<{self.__class__.__name__}({','.join(field_strings)})>"
        return f"<{self.__class__.__name__} {id(self)}>"
