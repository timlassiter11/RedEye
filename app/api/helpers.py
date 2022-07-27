from datetime import date, datetime
from typing import List, Type, TypeVar, Union
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


def _is_owner(**kwargs):
    id = kwargs.get("id")
    return current_user.id == int(id)


def owner_or_role_required(roles: Union[str, List[str]], is_owner = _is_owner):
    def decorator(func):
        @login_required
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_owner(**kwargs):
                return func(*args, **kwargs)
            return role_required(roles)(func)(*args, **kwargs)

        return wrapper

    return decorator

T = TypeVar('T')
def get_or_404(model: Type[T], id, message: str = "Resource not found") -> T:
    item = model.query.get(int(id))
    if item is None:
        json_abort(404, message=message)
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

def str_to_datetime(value: str) -> datetime:
    try:
        return parse(value)
    except ParserError:
        raise ValueError("Invalid datetime format")