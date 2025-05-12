from flask import Flask
from src.tetra_log.controller import tetra_bp
from src.stix.controller import stix_bp

def register_routes(app: Flask):
    app.register_blueprint(tetra_bp)
    app.register_blueprint(stix_bp)