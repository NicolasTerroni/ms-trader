import logging
from time import sleep
from flask import Blueprint, request
from flask.json import jsonify
import os, json

from project.models.init_db import db
from project.models.models import Buys, LastOperation, Sells

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

        params = {
            'symbol': data['symbol'],
            'side': 'BUY',
            'type': 'MARKET', # Siempre MARKET?
            'quantity': float(quantity),
        }

        response = dict() 
        


        # N BUY
        n_last_operation = LastOperation.query.filter_by(symbol=data['symbol'][:-4], user="N").first()
        if not n_last_operation:
            n_last_operation = LastOperation(
                symbol=data['symbol'][:-4],
                user = "N"
            )
            db.session.add(n_last_operation)
            db.session.commit()

        if n_last_operation.last_operation == "B":
            response["N_error"] = {"error": "No se permite comprar, la ultima operacion con esta moneda fue una compra."}
        else:
            try:
                n_order = n_client.create_test_order(**params)


                # SOLO PARA TESTING
                if len(n_order) == 0:
                    n_order['price'] = 1



                n_last_operation.price = n_order['price'] 
                n_last_operation.quantity = quantity
                n_last_operation.last_operation = "B"
                db.session.add(n_last_operation)
                
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
        


        # F BUY
        f_last_operation = LastOperation.query.filter_by(symbol=data['symbol'][:-4], user="F").first()
        if not f_last_operation:
            f_last_operation = LastOperation(
                symbol=data['symbol'][:-4],
                user = "F"
            )
            db.session.add(f_last_operation)
            db.session.commit()

        if f_last_operation.last_operation == "B":
            response["F_error"] = {"error": "No se permite comprar, la ultima operacion con esta moneda fue una compra."}
        else:
            try:
                f_order = f_client.create_test_order(**params)


                # SOLO PARA TESTING
                if len(f_order) == 0:
                    f_order['price'] = 1



                f_last_operation.price = f_order['price'] 
                f_last_operation.quantity = quantity
                f_last_operation.last_operation = "B"
                db.session.add(f_last_operation)
                
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
        asset_actual_market_price = f_client.get_symbol_ticker(symbol=data['symbol'])['price']
        
        response = dict()
        


        # N SELL
        n_last_operation = LastOperation.query.filter_by(symbol=data['symbol'][:-4], user="N").first()
        if n_last_operation.last_operation == "S":
            response["N_error"] = {"error": "No se permite vender, la ultima operacion con esta moneda fue una venta."}
        else:
            n_asset_amount = int(float(n_client.get_asset_balance(asset)['free']))
            n_last_buy_price = n_last_operation.price

            if float(n_last_buy_price) > float(asset_actual_market_price):
                response["N_error"] = {"error": "Se esta intentando vender a menos de lo que se gasto al comprar"}

            
            
            # SOLO PARA TESTING
            if n_asset_amount == 0:
                n_asset_amount = 10




            n_params = {
                'symbol': data['symbol'],
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': n_asset_amount,
                #'timeInforce': 'IOC',
                #'price': data['price'],
                }
        
            try:
                n_order = n_client.create_test_order(**n_params)
                


                # SOLO PARA TESTING
                if len(n_order) == 0:
                    n_order['price'] = 10



                n_sell = Sells(
                    symbol=data['symbol'][:-4],
                    price=n_order['price'],
                    quantity=n_asset_amount,
                    user = "N"
                    )
                db.session.add(n_sell)

                n_last_operation.last_operation = "S"
                n_last_operation.price = n_order['price']
                n_last_operation.quantity = n_asset_amount
                db.session.add(n_last_operation)

                db.session.commit()
                
                response['N_order'] = n_order

            except Exception as e: 
                response["N_error"] = {
                    "error": str(e),
                    "order_params": data,
                    "asset_actual_market_price": asset_actual_market_price,
                    "asset_last_buy_price": n_last_buy_price,
                    "asset_amount": n_asset_amount
                }
            finally:
                
                n_client.close_connection()
                print("Client N session closed.")
        


        # F SELL
        f_last_operation = LastOperation.query.filter_by(symbol=data['symbol'][:-4], user="F").first()
        if f_last_operation.last_operation == "S":
            response["F_error"] = {"error": "No se permite vender, la ultima operacion con esta moneda fue una venta."}
        else:
            f_asset_amount = int(float(n_client.get_asset_balance(asset)['free']))
            f_last_buy_price = n_last_operation.price

            if float(f_last_buy_price) > float(asset_actual_market_price):
                response["F_error"] = {"error": "Se esta intentando vender a menos de lo que se gasto al comprar"}


            # SOLO PARA TESTING
            if f_asset_amount == 0:
                f_asset_amount = 10


            f_params = {
                'symbol': data['symbol'],
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': f_asset_amount,
                #'timeInforce': 'IOC',
                #'price': data['price'],
                }
        
            try:
                f_order = f_client.create_test_order(**f_params)
                


                # SOLO PARA TESTING
                if len(f_order) == 0:
                    f_order['price'] = 10



                f_sell = Sells(
                    symbol=data['symbol'][:-4],
                    price=f_order['price'], 
                    quantity=f_asset_amount,
                    user = "F"
                    )
                db.session.add(f_sell)

                f_last_operation.last_operation = "S"
                f_last_operation.price = f_order['price']
                f_last_operation.quantity = f_asset_amount
                db.session.add(f_last_operation)

                db.session.commit()
                response['F_order'] = f_order


            except Exception as e: 
                response["F_error"] = {
                    "error": str(e),
                    "order_params": data,
                    "asset_actual_market_price": asset_actual_market_price,
                    "asset_last_buy_price": f_last_buy_price,
                    "asset_amount": f_asset_amount
                }
            finally:
                f_client.close_connection()
                print("Client F session closed.")
                
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

