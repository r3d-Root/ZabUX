from flask import Flask
from flasgger import Swagger
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()
    app = Flask(__name__)

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
    from .main.routes import main_bp
    from .api.routes import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
