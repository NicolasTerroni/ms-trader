# encoding: utf-8
from flask_script import Manager

from project.app import create_app

from decouple import config, UndefinedValueError

DB_LOCATION = config('DB_LOCATION') 

app = create_app(db_location=DB_LOCATION)

manager = Manager(app)

if __name__ == '__main__':
    manager.run()
