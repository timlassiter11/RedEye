from wtforms.validators import ValidationError

from app.models import Airplane, Airport


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
