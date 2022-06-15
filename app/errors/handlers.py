from app.errors import bp
from flask import render_template
from werkzeug.exceptions import HTTPException


@bp.app_errorhandler(HTTPException)
def handle_error(error):
    code = error.code
    return render_template(
        'errors/error.html',
        error_text=error.name,
        error_code=code
    ), code
