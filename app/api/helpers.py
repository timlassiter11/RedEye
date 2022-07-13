from datetime import date
from typing import List, Union
from dateutil.parser import parse, ParserError
from functools import wraps

from flask import jsonify
from flask_login import current_user
from flask_restful import abort

from app.models import Airport


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


def role_required(roles: Union[str, List[str]]):
    def decorator(func):
        @login_required
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.role in roles:
                json_abort(403, message="Forbidden")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def owner_or_role_required(roles: Union[str, List[str]]):
    def decorator(func):
        @login_required
        @wraps(func)
        def wrapper(*args, **kwargs):
            id = kwargs.get("id")
            if current_user.id == int(id):
                return func(*args, **kwargs)
            return role_required(roles)(func)(*args, **kwargs)

        return wrapper

    return decorator


def get_or_404(model, id):
    item = model.query.get(int(id))
    if item is None:
        json_abort(404, message="Resource not found")
    return item


def code_to_airport(code: str, error_message: str = None) -> Airport:
    airport = Airport.query.filter_by(code=code).first()
    if not airport:
        if not error_message:
            error_message = "Invalid airport code."
        raise ValueError(error_message)
    return airport


def str_to_date(value: str) -> date:
    try:
        return parse(value).date()
    except ParserError:
        raise ValueError("Invalid date format")
