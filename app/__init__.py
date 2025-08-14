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
    swagger_template = {
        "swagger": "2.0",
        "basePath": "/api",
        "info": {
            "title": "ZabUX API",
            "description": "Monitoring and Inventory Integration API",
            "version": "1.0"
        },
        "securityDefinitions": {
            "CustomHeader": {
                "type": "apiKey",
                "name": os.getenv("CUSTOM_AUTH_HEADER", "X-ZabUX-FE"),
                "in": "header",
                "description": "Required for all requests."
            },
            "ApiKeyHeader": {
                "type": "apiKey",
                "name": os.getenv("API_KEY_HEADER", "X-API-Key"),
                "in": "header",
                "description": "Only needed when your Origin is NOT on the allow-list."
            }
        },
        "security": [
            {"CustomHeader": []},                       # allowed-origin + custom header
            {"CustomHeader": [], "ApiKeyHeader": []}    # not-allowed origin -> need both
        ],
        "tags": [{"name": "System", "description": "Status & utilities"}],
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec_1",
                "route": "/apispec_1.json",
                "rule_filter": lambda rule: True,   # include all routes
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    }

    Swagger(app, template=swagger_template, config=swagger_config)

    # API Security
    allowed = [d.strip() for d in os.getenv("ALLOWED_DOMAINS", "").split(",") if d.strip()]
    api_keys = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

    app.config["ALLOWED_DOMAINS_SET"] = set(map(str.lower, allowed))
    app.config["API_KEYS_LIST"] = api_keys
    app.config["CUSTOM_AUTH_HEADER"] = os.getenv("CUSTOM_AUTH_HEADER", "X-RFP-Customer")
    app.config["API_KEY_HEADER"] = os.getenv("API_KEY_HEADER", "X-API-Key")
    
    # Register Blueprints
    from .views.view_routes import views_bp
    from .api.zabUX_routes import zabux_api_bp
    from .api.zabbix_routes import zabbix_api_bp
    from app.api.netbox_routes import netbox_api_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(zabux_api_bp, url_prefix='/api')
    app.register_blueprint(zabbix_api_bp, url_prefix='/api')
    app.register_blueprint(netbox_api_bp, url_prefix="/api")

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
