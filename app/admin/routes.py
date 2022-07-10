from app.admin import bp
from app.forms import AirplaneForm, AirportForm, FlightForm, UserEditForm
from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user


@bp.before_request
def restrict_bp_to_admins():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=url_for(request.endpoint)))

    if current_user.role != 'admin':
        abort(403)


@bp.route('/')
def home():
    return render_template('admin/home.html')


@bp.route('/customers')
def customers():
    form = UserEditForm()
    return render_template(
        'admin/users.html',
        title='Customers',
        form=form,
        api_endpoint='api.customers',
        role='Customer'
    )

@bp.route('/agents')
def agents():
    form = UserEditForm()
    return render_template(
        'admin/users.html',
        title='Agents',
        form=form,
        api_endpoint='api.agents',
        role='Agent'
    )

@bp.route('/admins')
def admins():
    form = UserEditForm()
    return render_template(
        'admin/users.html',
        title='Admins',
        form=form,
        api_endpoint='api.admins',
        role='Admin'
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