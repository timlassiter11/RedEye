from functools import wraps

from flask import jsonify
from flask_login import current_user
from flask_restful import abort


def json_abort(status_code, **kwargs):
    response = jsonify(**kwargs)
    response.status_code = status_code
    abort(response)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_anonymous:
            json_abort(401, message="Not authorized")
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @login_required
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            json_abort(403, message="Forbidden")
        return func(*args, **kwargs)

    return wrapper


def get_or_404(model, id):
    item = model.query.get(int(id))
    if item is None:
        json_abort(404, message="Resource not found")
    return item
