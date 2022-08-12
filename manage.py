# encoding: utf-8
from flask_script import Manager

from project.app import create_app

from decouple import config, UndefinedValueError

NICO_DB_LOCATION = config('NICO_DB_LOCATION') 
FRAN_DB_LOCATION = config('FRAN_DB_LOCATION') 

try:
    app = create_app(db_location=FRAN_DB_LOCATION)
except:
    app = create_app(db_location=NICO_DB_LOCATION)

manager = Manager(app)

if __name__ == '__main__':
    manager.run()
