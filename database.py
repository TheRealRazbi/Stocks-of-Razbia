from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# class UserDB(Base):
#     __tablename__ = 'user'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)
#
#
# class CompanyDB(Base):
#     __tablename__ = 'company'
#
#     id = Column(Integer, primary_key=True)
#     full_name = Column(String, nullable=False)
#     abbreviation = Column(String(4), nullable=False)
#
#

class SharesDB(Base):
    __tablename__ = 'shares'

    user_id = Column(ForeignKey('user.id'), primary_key=True)
    company_id = Column(ForeignKey('company.id'), primary_key=True)
    amount = Column(Integer, nullable=False)


if __name__ == '__main__':
    pass


