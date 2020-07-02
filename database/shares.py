from sqlalchemy import Column, ForeignKey
from sqlalchemy.sql import sqltypes as t

from .db import Base


class Shares(Base):
    __tablename__ = 'shares'

    user_id = Column(ForeignKey('user.id'), primary_key=True)

    company_id = Column(ForeignKey('company.id'), primary_key=True)

    amount = Column(t.Integer, nullable=False)

    def __repr__(self):
        return self._repr(
            id={
                "user": self.user_id,
                "company": self.company_id,
            },
            **self._getattrs("amount"),
        )
