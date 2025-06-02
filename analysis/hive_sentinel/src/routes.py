from flask import Flask
from src.tetra_log.controller import tetra_bp
from src.stix.controller import stix_bp
from src.kubescape_log.controller import kubescape_bp
from src.severity_analysis.controller import analysis_bp


def register_routes(app: Flask):
    app.register_blueprint(tetra_bp)
    app.register_blueprint(stix_bp)
    app.register_blueprint(kubescape_bp)
    app.register_blueprint(analysis_bp)
