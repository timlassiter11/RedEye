from app import db, models
from app.api import api
from app.api.helpers import get_or_404, json_abort, str_to_date
from app.email import send_email
from app.forms import PurchaseTransactionForm
from app.helpers import calculate_taxes
from flask import render_template, session
from flask_login import current_user
from flask_restful import Resource, request


@api.resource("/checkout")
class Checkout(Resource):
    def post(self):
        form = PurchaseTransactionForm(data=request.json)
        if form.validate():
            # Get itinerary from session data
            itineraries = session["itineraries"]
            itinerary = itineraries.get(form.itinerary.data)
            if itinerary is None:
                json_abort(404, message="Quote is not longer valid")

            flights = [
                get_or_404(
                    models.Flight, id, "One ore more flights are no longer available."
                )
                for id in itinerary["flights"]
            ]
            departure_date = str_to_date(itinerary["departure_date"])

            user = models.User.query.filter_by(email=form.email.data).first()

            transaction = models.PurchaseTransaction()
            # TODO: What if the user is logged in? Should we use their email instead?
            transaction.email = form.email.data
            transaction.confirmation_number = transaction.generate_confirmation_number(
                form.email.data
            )
            transaction.departure_date = departure_date
            transaction.departure_id = itinerary["departure_airport"]
            transaction.destination_id = itinerary["destination_airport"]

            form_user = -1
            if user is not None:
                form_user = user.id
                if user.role in ["admin", "agent"]:
                    # TODO: Should employees be able to use their work accounts to purchase tickets?
                    # Maybe they get a discount if they do?
                    pass

            session_user = -1
            if not current_user.is_anonymous and current_user.role == "agent":
                session_user = current_user.id

            # If session_user is an agent we want to give them credit for the sale
            # unless they are purchasing it themselves.
            if form_user != session_user and session_user != -1:
                transaction.assisted_by = session_user

            num_of_passengers = len(form.passengers)

            base_fare = 0
            for flight in flights:
                if not flight.available_seats(departure_date) >= num_of_passengers:
                    json_abort(
                        400, message=f"Flight {flight.number} is no longer available"
                    )

                price = flight.cost(departure_date)

                for passenger in form.passengers:
                    ticket = models.PurchasedTicket()
                    ticket.first_name = passenger.first_name.data
                    ticket.middle_name = passenger.middle_name.data
                    ticket.last_name = passenger.last_name.data
                    ticket.date_of_birth = passenger.date_of_birth.data
                    ticket.gender = passenger.gender.data
                    ticket.flight_id = flight.id
                    ticket.purchase_price = price
                    transaction.tickets.append(ticket)

                    base_fare += price

            transaction.purchase_price = base_fare + calculate_taxes(
                base_fare, len(flights)
            )

            db.session.add(transaction)
            db.session.commit()
            db.session.refresh(transaction)

            itinerary = models.TripItinerary(
                transaction.departure_date, transaction.flights
            )

            send_email(
                "Your Purchase Confirmation",
                [transaction.email],
                render_template(
                    "email/purchase_confirmation.txt",
                    transaction=transaction,
                    itinerary=itinerary,
                ),
                render_template(
                    "email/purchase_confirmation.html",
                    transaction=transaction,
                    itinerary=itinerary,
                ),
            )

            return transaction.to_dict(expand=True)

        json_abort(400, message=form.errors)
