from flask import Blueprint, jsonify, current_app
from app.api.security import secure_endpoint

zabbix_api_bp = Blueprint('zabiix_api', __name__)

@zabbix_api_bp.route('/status', methods=['GET', "OPTIONS"])
@secure_endpoint()
def status():
    """
    Simple test message
    ---
    tags:
        - Testing
    responses:
        200:
            description: Simple test message
    """
    current_app.logger.info("Status endpoint hit")
    return jsonify({'status': 'ok', 'message': 'API is working'})
