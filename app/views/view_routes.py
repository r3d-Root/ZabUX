from flask import Blueprint, render_template, current_app

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    current_app.logger.info("Index page hit")
    return render_template('index.html')
