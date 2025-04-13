from flask import render_template
from flask_login import current_user

def index():
    """Handle the index/dashboard page"""
    return render_template('index.html')