import bcrypt
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

engine = db.create_engine("mysql://armin:T101vb$!GuYX@ub.pxnet.de/telegram_bot", echo=True)
connection = engine.connect()

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'
    id = db.Column(db.String(256), primary_key=True)
    username = db.Column(db.String(40))
    message = db.Column(db.String(3072))
    date = db.Column(db.Date)

class Admin(Base):
    __tablename__ = 'admins'
    username = db.Column(db.String(40), primary_key=True)
    password = db.Column(db.String(256))

class User(Base):
    __tablename__ = 'users'
    username = db.Column(db.String(40), primary_key=True)
    password = db.Column(db.String(256))
    creator = db.Column(db.ForeignKey(Admin.username, ondelete='CASCADE'))

class Account(Base):
    __tablename__ = 'accounts'

    username = db.Column(db.String(20), primary_key=True)
    password = db.Column(db.String(256))
    host = db.Column(db.String)
    creator = db.Column(db.ForeignKey(User.username, ondelete='CASCADE'))
    created_date = db.Column(db.Date)
    created_time = db.Column(db.Time)
    expiration = db.Column(db.Date)
    month = db.Column(db.Integer)


account = relationship('User', foreign_keys='Account.creator')
user = relationship('Admin', foreign_keys='User.creator')
Base.metadata.create_all(engine)

