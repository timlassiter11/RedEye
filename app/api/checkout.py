from flask_login import current_user
from app import db, models
from app.api import api
from app.api.helpers import json_abort
from app.forms import PurchaseTransactionForm
from flask_restful import Resource, request

@api.resource("/checkout")
class Checkout(Resource):
    def post(self):
        form = PurchaseTransactionForm(data=request.json)
        if form.validate():
            user = models.User.query.filter_by(email=form.email.data).first()

            transaction = models.PurchaseTransaction()
            # TODO: What if the user is logged in? Should we use their email instead?
            transaction.email = form.email.data

            form_user = -1
            if user is not None:
                form_user = user.id
                if user.role in ['admin', 'agent']:
                    # TODO: Should employees be able to use their work accounts to purchase tickets?
                    # Maybe they get a discount if they do?
                    pass
            
            session_user = -1
            if not current_user.is_anonymous and current_user.role == 'agent':        
                session_user = current_user.id

            # If session_user is an agent we want to give them credit for the sale
            # unless they are purchasing it themselves.
            if form_user != session_user and session_user != -1:
                transaction.assisted_by = session_user
                
            departure_date = form.departure_date.data
            num_of_passengers = len(form.passengers)

            total_price = 0
            for field in form.flights:
                flight = field.data
                if not flight.available_seats(departure_date) >= num_of_passengers:
                    json_abort(400, message=f'Flight {flight.number} is no longer available')

                price = flight.cost(departure_date)

                for passenger in form.passengers:
                    ticket = models.PurchasedTicket()
                    ticket.first_name = passenger.first_name.data
                    ticket.middle_name = passenger.middle_name.data
                    ticket.last_name = passenger.last_name.data
                    ticket.date_of_birth = passenger.date_of_birth.data
                    ticket.gender = passenger.gender.data
                    ticket.departure_date = departure_date
                    ticket.flight_id = flight.id
                    ticket.purchase_price = price
                    transaction.tickets.append(ticket)
                    total_price += price

            db.session.add(transaction)
            db.session.commit()
            db.session.refresh(transaction)
            return "", 204
        
        json_abort(400, message=form.errors)