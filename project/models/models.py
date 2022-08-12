from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Integer, String, DateTime, Float
from project.models.init_db import db


# para guardar las ultimas compras de cada moneda
class LastBuys(db.Model):
    __tablename__ = 'last_buys'
    id = db.Column(Integer, primary_key=True, autoincrement=True)

    symbol = db.Column(String, nullable=False, unique=True)
    price = db.Column(Float)
    quantity = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)

    last_operation = db.Column(String)

# para guardar todas las compras que se hagan
class Buys(db.Model):
    __tablename__ = 'buys'
    id = db.Column(Integer, primary_key=True, autoincrement=True)

    symbol = db.Column(String, nullable=False)
    price = db.Column(Float)
    quantity = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)

# para guardar todas las ventas que se hagan
class Sells(db.Model):
    __tablename__ = 'sells'
    id = db.Column(Integer, primary_key=True, autoincrement=True)

    symbol = db.Column(String, nullable=False)
    price = db.Column(Float)
    quantity = db.Column(Float)

    date = db.Column(DateTime, server_default=db.func.now())
    user = db.Column(String)

