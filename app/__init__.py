from flask import Flask
from flasgger import Swagger
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler


def create_app():
    load_dotenv()
    app = Flask(__name__)

    # Logging setup
    configure_logging(app)

    # Swagger setup
    Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "ZabUX API",
            "description": "Monitoring and Inventory Integration API",
            "version": "1.0"
        },
        "basePath": "/api",  # All endpoints under /api
    })

    
    # Register Blueprints
    from .views.routes import main_bp
    from .api.zabUX_routes import zabbix_api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(zabbix_api_bp, url_prefix='/api')

    return app


def configure_logging(app):
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'zabUX.log'),
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    file_handler.setFormatter(formatter)

    # Remove default handlers to avoid duplicate logs
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(logging.StreamHandler())  # Also log to console

    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.info("Logger initialized")
