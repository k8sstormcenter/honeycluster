from flask import Flask
from src.routes import register_routes
from src.etl.controller import start_stix_etls

def create_app():
    app = Flask(__name__)
    register_routes(app)

    start_stix_etls()

    return app
