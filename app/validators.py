from wtforms.validators import ValidationError

from app.models import Airplane, Airport, Flight, User


class UniqueEmailValidator:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if User.query.filter_by(email=field.data).count() > 0:
            message = self.message or "An account with that email already exists"
            raise ValidationError(message)


class UserValidator:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        user = User.query.filter_by(email=field.data).first()
        if not user:
            message = self.message or "An account with that email doesn't exists."
            raise ValidationError(message)
        field.data = user


class AirplaneValidator:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        airplane = Airplane.query.filter_by(registration_number=field.data).first()
        if not airplane:
            message = self.message or "No plane with that registration number exists"
            raise ValidationError(message)
        field.data = airplane


class AirportValidator:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        airport = Airport.query.filter_by(code=field.data).first()
        if not airport:
            message = self.message or "No airport with that code exists"
            raise ValidationError(message)
        field.data = airport

class FlightValidator:
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        flight = Flight.query.filter_by(number=field.data).first()
        if not flight:
            message = self.message or "Invalid flight id"
            raise ValidationError(message)
        field.data = flight

