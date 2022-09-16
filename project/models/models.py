from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Integer, String, DateTime, Float
from project.models.init_db import db



class LastOperation(db.Model):
    __tablename__ = 'last_operation'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    last_operation = db.Column(String)

    symbol = db.Column(String, nullable=False)
    price = db.Column(Float)
    quantity = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)



class Buys(db.Model):
    __tablename__ = 'buys'
    id = db.Column(Integer, primary_key=True, autoincrement=True)

    symbol = db.Column(String, nullable=False)
    unit_price = db.Column(Float)
    quantity = db.Column(Float)
    commission = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)



class Sells(db.Model):
    __tablename__ = 'sells'
    id = db.Column(Integer, primary_key=True, autoincrement=True)

    symbol = db.Column(String, nullable=False)
    unit_price = db.Column(Float)
    quantity = db.Column(Float)
    commission = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)


# when selling, we register earnings in the database
class Earns(db.Model):
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(String, nullable=False)
    earns = db.Column(Float)
    
    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)
