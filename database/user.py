from sqlalchemy import Column
from sqlalchemy.sql import sqltypes as t
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = 'user'

    id = Column(t.Integer, primary_key=True)
    name = Column(t.String, nullable=False)

    shares = relationship("Shares", backref="user", passive_deletes=True)

    def __str__(self):
        return f'username: "{self.name}"'

    def __repr__(self):
        return self._repr(
            **self._getattrs("id", "name", "shares"),
        )

