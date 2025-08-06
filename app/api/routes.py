from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
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
    return jsonify({'status': 'ok', 'message': 'API is working'})
