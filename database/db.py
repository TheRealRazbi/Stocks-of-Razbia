import typing

__all__ = ["engine", "Session", "Base"]
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, exc


class _Base:
    def __repr__(self) -> str:
        return self._repr(**self._getattrs("id"))

    def _getattrs(self, *attrs: str):
        return {attr: getattr(self, attr) for attr in attrs}

    def _repr(self, **fields: typing.Any) -> str:
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


engine = create_engine('sqlite:///db.sqlite', echo=True)
Session = sessionmaker(bind=engine)
Base: typing.Type[_Base] = declarative_base(bind=engine, cls=_Base)

