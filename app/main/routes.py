import datetime as dt
from typing import List

from app.api.helpers import code_to_airport, str_to_date
from app.forms import PurchaseTransactionForm, TransactionRefundForm
from app.main import bp
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import PurchaseTransaction, TripItinerary


@bp.route("/")
def home():
    return render_template(
        "main/index.html",
        title="Red Eye",
    )


@bp.route("/search")
def search():
    args = request.args.copy()

    departure_code = args.get("departure_code")
    arrival_code = args.get("arrival_code")
    departure_date = args.get("departure_date")
    num_of_passengers = args.get("num_of_passengers", 1)

    args["expand"] = True

    try:
        departure = code_to_airport(departure_code, "Invalid departure airport.")
        arrival = code_to_airport(arrival_code, "Invalid destination airport.")
        date = str_to_date(departure_date)

        if departure.id == arrival.id:
            raise ValueError("Departure and arrival airports cannot be the same.")

        if date < dt.datetime.utcnow().date():
            raise ValueError("Departure date must be in the future.")

        try:
            num_of_passengers = int(num_of_passengers)
        except ValueError:
            raise ValueError("Number of passengers must be a number.")

        if num_of_passengers < 1 or num_of_passengers > 5:
            raise ValueError("Number of passengers must be between 1 and 5.")

    except ValueError as e:
        # TODO: How do we handle bad arguments?
        # They are required for the search to work.
        flash(str(e), "danger")
        return redirect(
            url_for(
                "main.home",
            )
        )

    return render_template(
        "main/searchresults.html",
        title="Search Flights",
        departure=departure,
        arrival=arrival,
        date=date,
        passengers=num_of_passengers,
        args=args,
    )


@bp.route("/checkout")
def checkout():
    form = PurchaseTransactionForm()

    # Agents can enter information for customers. If it's an agent we don't want
    # them to be forced to use their email. That wouldn't make sense.
    if not current_user.is_anonymous and current_user.role != "agent":
        form.email.data = current_user.email
        if form.email.render_kw is None:
            form.email.render_kw = {}
        form.email.render_kw["readonly"] = "readonly"

        form.passengers[0].first_name.data = current_user.first_name
        form.passengers[0].last_name.data = current_user.last_name

    return render_template("main/checkout.html", title="Checkout", form=form)


@bp.route("/mytrips")
@login_required
def my_trips():

    upcoming_trips = []
    purchase_history = []

    purchases: List[PurchaseTransaction] = current_user.purchases(dt.date.today())
    for trip in purchases:
        itinerary = TripItinerary(
            trip.departure_date,
            trip.flights
        )

        if not trip.refunded:
            form = TransactionRefundForm(tickets=[ticket.id for ticket in trip.tickets])
            upcoming_trips.append((itinerary, trip, form))
        else:
            purchase_history.append((itinerary, trip))

    purchases: List[PurchaseTransaction] = current_user.purchases(None, dt.date.today())
    for trip in purchases:
        itinerary = TripItinerary(
            trip.departure_date,
            trip.flights
        )
        purchase_history.append((itinerary, trip))

    return render_template(
        "main/mytrips.html", upcoming_trips=upcoming_trips, purchase_history=purchase_history
    )


@bp.route("/contact")
def contact():
    return render_template("main/contact.html")


@bp.route("/catalog")
def catalog():
    return render_template("main/catalog.html", title="Flights")
