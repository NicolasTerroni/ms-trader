from flask import Flask
from project.models.init_db import db
from project.routes import trader_api
from decouple import config, UndefinedValueError

DB_LOCATION = config('DB_LOCATION') 

# App setup and config
def create_app(db_location):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_location
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.register_blueprint(trader_api)
    db.init_app(app)

    with app.app_context():  
        db.create_all()
    return app

if __name__ == "__main__":
    app = create_app(db_location=DB_LOCATION)
    app.run(debug=True)

