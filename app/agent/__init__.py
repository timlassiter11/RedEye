from flask import Blueprint

bp = Blueprint('agent', __name__, template_folder='templates')

from app.agent import routes