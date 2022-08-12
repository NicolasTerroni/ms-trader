import logging
from time import sleep
from flask import Blueprint, request
from flask.json import jsonify
import os, json

from project.models.init_db import db
from project.models.models import Buys, LastBuys, Sells

from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from datetime import datetime, timedelta
from decouple import config


trader_api = Blueprint('users',__name__)

# obtener de variables de entorno 
F_API_KEY = config('F_API_KEY') #os.getenv('API_KEY')
F_API_SECRET = config('F_API_SECRET')  #os.getenv('API_SECRET')
N_API_KEY = config('N_API_KEY') #os.getenv('API_KEY')
N_API_SECRET = config('N_API_SECRET')  #os.getenv('API_SECRET')

USDT_BUY_AMOUNT = int(config('USDT_BUY_AMOUNT')) #os.getenv('USDT_BUY_AMOUNT')




"""
--- LOGICA DE NEGOCIO ---

Levantar una sqlite3 para:

- Registrar precio y cantidad de ultima compras de cada moneda
- Registrar todas las compras
- Registrar todas las ventas

Confirmar que lo gastado al comprar sea menor que lo ganado al vender, nunca se venderia 
a menos que estes ganando $. Osea comparando el precio unitario de la ultima compra y asegurandose
de estar vendiendo a mas.

Preguntas:
Esto no puede trabar operaciones si la moneda sufre una gran baja de valor?
Guardar registro de las operaciones fallidas?

symbols = [
    BTC, 
    WAVES, 
    BNB, 
    AVAX, 
    DOT, 
    MOVR, 
    SOL, 
    KSM
]
"""

"""
--- ENDPOINTS UTILES DE PYTHON BINANCE ---

# get all symbol prices
prices = client.get_all_tickers()

# get all orders
orders = client.get_all_orders(symbol='BNBBTC', limit=10)

# get open orders
orders = client.get_open_orders(symbol='RVNUSDT')        

"""

# TEST ORDER
@trader_api.route('/test_order', methods=['POST'])
def test_order():
    f_client = Client(F_API_KEY,F_API_SECRET)
    n_client = Client(N_API_KEY,N_API_SECRET)
    print("Client sessions created.")

    data = request.get_json()
    symbol_info = f_client.get_symbol_info(data['symbol'])
    
    if data['side'] == 'BUY':

        # AVG_PRICE (price thats used for market orders)
        avg_price = float(n_client.get_avg_price(symbol=data['symbol'])['price'])

        # MIN_NOTIONAL
        min_notional = float(symbol_info["filters"][3]["minNotional"]) + 20
        quantity = min_notional / avg_price

        # ASSET_PRECISION
        if int(symbol_info["filters"][2]["minQty"].split(".")[0]) == 0:
            decimals = symbol_info["filters"][2]["minQty"].split(".")[1]
            round_to = decimals.find("1") + 1
            if len(str(quantity).split(".")[1]) > symbol_info['baseAssetPrecision']:
                quantity = float(round(quantity,round_to))
        else:
            quantity = float(symbol_info["filters"][2]["minQty"])

        #import ipdb; ipdb.set_trace()
        
        # LOT_SIZE
        min_quantity_allowed = float(symbol_info["filters"][2]["minQty"])
        if quantity < min_quantity_allowed:
            return jsonify({
                "error": "La cantidad es menor a la minima permitida del activo",
                "filterType": symbol_info["filters"][2]["filterType"],
                })
        
        # MARKET_LOT_SIZE
        market_min_quantity_allowed = float(symbol_info['filters'][5]['minQty'])
        if quantity < market_min_quantity_allowed:
            return jsonify({"error": "La cantidad es menor a la minima permitida del activo",
                "filterType": symbol_info["filters"][5]["filterType"],
                })
        
        # incrementador de cantidad hasta alcanzar el minimo permitido
        #step_size_quantity = float(symbol_info['filters'][5]['stepSize'])
        #while quantity < min_quantity_allowed:
        #    min_quantity_allowed += step_size_quantity

        params = {
            'symbol': data['symbol'],
            'side': 'BUY',
            'type': 'MARKET', # Siempre MARKET?
            'quantity': float(quantity),
        }

        #import ipdb; ipdb.set_trace()

        response = dict() 
        try:
            
            n_order = n_client.create_test_order(**params)

            last_buy = LastBuys.query.filter_by(symbol=data['symbol'][:-4]).first()
            if not last_buy:
                last_buy = LastBuys(
                    symbol=data['symbol'][:-4],
                    price=n_order['price'], 
                    quantity=quantity,
                    user = "N"
                )
                db.session.add(last_buy)
            else:
                last_buy.symbol = data['symbol'][:-4]
                last_buy.price = n_order['price'] 
                last_buy.quantity = quantity
                last_buy.last_operation = "B"
                db.session.add(last_buy)
            
            buy = Buys(
                symbol= data['symbol'][:-4],
                price= n_order['price'],
                quantity= quantity,
                user = "N"
            )
            db.session.add(buy)
            print("N order placed.")
            response["N_order"] = n_order
            
        except Exception as e: 
            response["N_error"] = {
                "error": str(e),
                "order_params": data,
                "asset_last_price": avg_price,
                "quantity": quantity
            }
        finally:
            n_client.close_connection()
            print("Client N session closed.")
            
        try:
            f_order = f_client.create_test_order(**params)
            last_buy = LastBuys.query.filter_by(symbol=data['symbol'][:-4]).first()
            if not last_buy:
                last_buy = LastBuys(
                    symbol=data['symbol'][:-4],
                    price=f_order['price'], 
                    quantity=quantity,
                    user = "F"
                )
                db.session.add(last_buy)
            else:
                last_buy.symbol = data['symbol'][:-4]
                last_buy.price = f_order['price'] 
                last_buy.quantity = quantity
                last_buy.last_operation = "B"
                db.session.add(last_buy)
            
            buy = Buys(
                symbol= data['symbol'][:-4],
                price= f_order['price'], 
                quantity= quantity,
                user = "F"
            )
            db.session.add(buy)
            print("F order placed.")

            response["F_order"] = f_order

        except Exception as e: 
            response["F_error"] = {
                "error": str(e),
                "order_params": data,
                "asset_last_price": avg_price,
                "quantity": quantity
            }
        finally:
            f_client.close_connection()
            print("Client F session closed.")

        db.session.commit() 
        return jsonify(response)    

    elif data['side'] == 'SELL':

        asset = data['symbol'][:-4]
        f_asset_amount = int(float(f_client.get_asset_balance(asset)['free']))
        n_asset_amount = int(float(n_client.get_asset_balance(asset)['free']))

        asset_actual_market_price = f_client.get_symbol_ticker(symbol=data['symbol'])['price']
        
        last_buy = LastBuys.query.filter_by(symbol=data['symbol'][:-4]).first()
        asset_last_buy_price = last_buy.price

        if not asset_last_buy_price:
            asset_last_buy_price = 0
        
        if float(asset_last_buy_price) > float(asset_actual_market_price):
            return jsonify({"message": "Se esta intentando vender a menos de lo que se gasto al comprar"})
        
        if last_buy.last_operation == "S":
            return jsonify({"message": "No se permite vender, la ultima operacion con esta moneda fue una venta."})

        f_params = {
            'symbol': data['symbol'],
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': f_asset_amount,
            #'timeInforce': 'IOC',
            #'price': data['price'],
            }        
        n_params = {
            'symbol': data['symbol'],
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': n_asset_amount,
            #'timeInforce': 'IOC',
            #'price': data['price'],
            }
        
        response = dict()
        try:
            order = f_client.create_test_order(**f_params)
            
            sell = Sells(
                symbol=data['symbol'][:-4],
                price=order['price'], # o de donde sea que se saque
                quantity=f_asset_amount,
                # user = user (cuando implementemos doble usuario)
                )
            db.session.add(sell)

            last_buy.last_operation = "S"
            db.session.add(last_buy)

            db.session.commit()

        except Exception as e: 
            response["F_error"] = {
                "error": str(e),
                "order_params": data,
                "asset_actual_market_price": asset_actual_market_price,
                "asset_last_buy_price": asset_last_buy_price,
                "asset_amount": f_asset_amount
            }
        finally:
            f_client.close_connection()
            print("Client F session closed.")

        
        try:
            order = n_client.create_test_order(**n_params)
            
            sell = Sells(
                symbol=data['symbol'][:-4],
                price=order['price'], # o de donde sea que se saque
                quantity=n_asset_amount,
                # user = user (cuando implementemos doble usuario)
                )
            db.session.add(sell)

            last_buy.last_operation = "S"
            db.session.add(last_buy)

            db.session.commit()

        except Exception as e: 
            response["N_error"] = {
                "error": str(e),
                "order_params": data,
                "asset_actual_market_price": asset_actual_market_price,
                "asset_last_buy_price": asset_last_buy_price,
                "asset_amount": n_asset_amount
            }
        finally:
            n_client.close_connection()
            print("Client N session closed.")
        
        db.session.commit() 
        return jsonify(response)    

    
    else:
        return jsonify({"error": "Side can only be BUY/SELL"})





# ORDER

@trader_api.route('/order', methods=['POST'])
def make_order():
    try:
        data = request.get_json()
        params = {
            'symbol': data['symbol'],
            'side': data['side'],
            'type': data['type'],
            'quantity': data['quantity'],
            'timeInforce': data['timeInforce'],
            'price': data['price']
            }
    except KeyError: 
        return jsonify({"error": "No se recibieron los parametros necesarios"})
    try:
        import ipdb; ipdb.set_trace()
        order = None
        #order = client.create_order(**params)
    except Exception as e: 
        return jsonify({"error": str(e)})

    return jsonify({"order": order})

