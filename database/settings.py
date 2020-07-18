from sqlalchemy import Column, select, func
from sqlalchemy.sql import sqltypes as t

from .db import Base


class Settings(Base):
    __tablename__ = 'settings'

    key = Column(t.String, primary_key=True)
    value = Column(t.String, nullable=False)






