from flask import Blueprint, render_template

shared_bp = Blueprint('shared', __name__)

@shared_bp.route('/')
def home():
    return render_template('home.html')
