import pytz
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    FloatField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TimeField,
    DateField,
)
from wtforms.validators import (
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    ValidationError,
)

from app.fields import TypeaheadField
from app.validators import AirplaneValidator, AirportValidator


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    first_name = StringField("First Name", validators=[InputRequired()])
    last_name = StringField("Last Name", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField(
        "Confirm Password",
        validators=[
            InputRequired(),
            EqualTo("password", message="Passwords do not match"),
        ],
    )
    submit = SubmitField("Register")


class ResetPasswordRequestForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    submit = SubmitField("Request")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField(
        "Confirm Password",
        validators=[
            InputRequired(),
            EqualTo("password", message="Passwords do not match"),
        ],
    )
    submit = SubmitField("Reset Password")


class MethodForm(FlaskForm):
    """Form with a hidden field containing the form method.
    Used for handling method types not supported by standard
    browsers such as DELETE and PUT.
    """

    method = HiddenField(default="POST")

    def validate(self, extra_validators=None):
        if self.method.data == "DELETE":
            return self.csrf_token.validate(self)
        return super().validate(extra_validators=extra_validators)


class UserEditForm(MethodForm):
    email = EmailField("Email", validators=[InputRequired()])
    first_name = StringField("First Name", validators=[InputRequired()])
    last_name = StringField("Last Name", validators=[InputRequired()])


class AdminUserEditForm(UserEditForm):
    role = SelectField(
        "Role", choices=[("user", "User"), ("agent", "Agent"), ("admin", "Admin")]
    )


class AirportForm(FlaskForm):
    code = StringField("Code", validators=[InputRequired(), Length(min=3, max=3)])
    name = StringField("Name", validators=[InputRequired()])
    timezone = SelectField(
        "Timezone", choices=[(tz, tz) for tz in pytz.common_timezones]
    )
    latitude = FloatField("Latitude", validators=[InputRequired()])
    longitude = FloatField("Longitude", validators=[InputRequired()])
    city = StringField("City")
    state = StringField("State")


class AirplaneForm(FlaskForm):
    registration_number = StringField(
        "Registration Number", validators=[InputRequired()]
    )
    model_name = StringField("Model Name", validators=[InputRequired()])
    model_code = StringField("Model Code", validators=[InputRequired()])
    capacity = IntegerField(
        "Capacity", validators=[InputRequired(), NumberRange(min=0)]
    )
    range = IntegerField("Range", validators=[InputRequired(), NumberRange(min=0)])


class FlightForm(FlaskForm):
    number = StringField(
        "Flight Number", validators=[InputRequired(), Length(min=1, max=4)]
    )
    airplane = TypeaheadField("Plane", validators=[InputRequired(), AirplaneValidator()])
    departure_airport = TypeaheadField("Departing From", validators=[InputRequired(), AirportValidator()])
    arrival_airport = TypeaheadField("Arriving To", validators=[InputRequired(), AirportValidator()])
    departure_time = TimeField("Departing Time", validators=[InputRequired()])
    start = DateField("Start", validators=[InputRequired()])
    end = DateField("End", validators=[InputRequired()])

    def validate_end(form, _):
        if form.start.data >= form.end.data:
            raise ValidationError("End date must come after start date")
