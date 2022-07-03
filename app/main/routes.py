from app.main import bp
from flask import render_template, url_for, redirect, render_template
from app.forms import AirplaneForm, AirportForm, FlightForm, UserEditForm

@bp.route('/')
def home():
    return render_template(
        'main/index.html',
        title='Red Eye',
    )



@bp.route('/contact')
def contact():
    return render_template('main/contact.html')

@bp.route('/catalog')
def catalog():
    form = FlightForm()
    return render_template('main/catalog.html',
        title='Flights',
        form=form
    )