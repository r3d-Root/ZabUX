from flask import Blueprint, jsonify, current_app
from app.api.security import secure_endpoint

zabux_api_bp = Blueprint('zabux_api', __name__)

@zabux_api_bp.route('/status', methods=['GET', "OPTIONS"])
@secure_endpoint()
def status():
    """
    Simple test message
    ---
    tags:
        - ZabUX
    security:
      - CustomHeader: []
        ApiKeyHeader: []
    responses:
        200:
            description: Simple test message
    """
    current_app.logger.info("Status endpoint hit")
    return jsonify({'status': 'ok', 'message': 'API is working'})


