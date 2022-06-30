from app import db
from app.admin import bp
from app.forms import AirplaneForm, AirportForm, FlightForm, UserEditForm
from app.models import User
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError


@bp.before_request
def restrict_bp_to_admins():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=url_for(request.endpoint)))

    if current_user.role != 'admin':
        abort(403)


@bp.route('/')
def home():
    return render_template('admin/home.html')


@bp.route('/users')
def users():
    # TODO: Separate user page into customer, agent, and admin tabs
    user_form = UserEditForm()
    return render_template(
        'admin/users.html',
        title='Users',
        users=User.query.all(),
        user_form=user_form
    )


@bp.route('/airports')
def airports():
    form = AirportForm()
    return render_template(
        'admin/airports.html',
        title='Airports',
        form=form,
    )


@bp.route('/airplanes')
def airplanes():
    form = AirplaneForm()
    return render_template(
        'admin/airplanes.html',
        title='Airplanes',
        form=form,
    )


@bp.route('/flights')
def flights():
    form = FlightForm()
    return render_template(
        'admin/flights.html',
        title='Flights',
        form=form
    )