from app.api.helpers import code_to_airport, str_to_date
from app.main import bp
from flask import redirect, render_template, request, url_for


@bp.route('/')
def home():
    return render_template(
        'main/index.html',
        title='Red Eye',
    )

@bp.route('/search')
def search():
    args = request.args.copy()

    departure_code = args.get("departure_code")
    arrival_code = args.get("arrival_code")
    departure_date = args.get("departure_date")
    num_of_passengers = args.get("num_of_passengers", 1)

    args['expand'] = True

    try:
        departure = code_to_airport(departure_code)
        arrival = code_to_airport(arrival_code)
        date = str_to_date(departure_date)
    except ValueError:
        # TODO: How do we handle bad arguments? 
        # They are required for the search to work.
        return redirect(url_for('main.home'))

    return render_template(
        'main/searchresults.html',
        title='Search Flights',
        departure=departure,
        arrival=arrival,
        date=date,
        passengers=num_of_passengers,
        args=args
    )

@bp.route('/checkout')
def checkout():
    return render_template(
        'main/checkout.html',
        title='Checkout',
    )