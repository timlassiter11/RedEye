import pytz
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    FieldList,
    FloatField,
    FormField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TimeField,
)
from wtforms.validators import (
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    ValidationError,
)
from wtforms.widgets import HiddenInput

from app.fields import TypeaheadField
from app.validators import (
    AirplaneValidator,
    AirportValidator,
    UniqueEmailValidator,
    UserValidator,
)


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), UserValidator()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")


class RegistrationForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), UniqueEmailValidator()])
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


class ResetPasswordRequestForm(FlaskForm):
    email = EmailField(
        "Email", validators=[InputRequired(), UserValidator(populate_field=False)]
    )


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField(
        "Confirm Password",
        validators=[
            InputRequired(),
            EqualTo("password", message="Passwords do not match"),
        ],
    )


class UserEditForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), UniqueEmailValidator()])
    first_name = StringField("First Name", validators=[InputRequired()])
    last_name = StringField("Last Name", validators=[InputRequired()])
    password = PasswordField("Password")
    password2 = PasswordField(
        "Confirm Password",
        validators=[EqualTo("password", message="Passwords do not match")],
    )

    def populate_obj(self, obj):
        pass1 = self.password.data

        del self.password
        del self.password2

        if pass1 and hasattr(obj, "set_password"):
            obj.set_password(pass1)

        return super().populate_obj(obj)


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
    airplane = TypeaheadField(
        "Plane", validators=[InputRequired(), AirplaneValidator()]
    )
    departure_airport = TypeaheadField(
        "Departing From", validators=[InputRequired(), AirportValidator()]
    )
    arrival_airport = TypeaheadField(
        "Arriving To", validators=[InputRequired(), AirportValidator()]
    )
    departure_time = TimeField("Departing Time", validators=[InputRequired()])
    start = DateField("Start", validators=[InputRequired()])
    end = DateField("End", validators=[InputRequired()])

    def validate_end(form, _):
        if form.start.data >= form.end.data:
            raise ValidationError("End date must come after start date")


class PassengerForm(FlaskForm):
    first_name = StringField("First Name", validators=[InputRequired()])
    middle_name = StringField("Middle Name")
    last_name = StringField("Last Name", validators=[InputRequired()])
    date_of_birth = DateField("Date of Birth", validators=[InputRequired()])
    gender = SelectField("Gender", choices=[("male", "Male"), ("female", "Female")])


class PurchaseTransactionForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    country = SelectField(
        "Country",
        choices=[(key, value) for key, value in pytz.country_names.items()],
        default="US",
    )
    street_address = StringField("Street Address", validators=[InputRequired()])
    street_address2 = StringField("Street Address 2")
    city = StringField("City/Town", validators=[InputRequired()])
    state = StringField("State/Province/Region", [InputRequired()])
    zip_code = StringField("Zip Code", validators=[InputRequired()])
    card_number = StringField("Card Number", validators=[InputRequired()])
    card_expiration = StringField("MM/YYYY", validators=[InputRequired()])
    card_cvc = StringField("CVC", validators=[InputRequired()])
    passengers = FieldList(FormField(PassengerForm), min_entries=1)
    itinerary = HiddenField()


class TransactionRefundForm(FlaskForm):
    tickets = FieldList(IntegerField(widget=HiddenInput()), min_entries=1)
