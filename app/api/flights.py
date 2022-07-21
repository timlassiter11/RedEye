import datetime as dt
from distutils.util import strtobool

from app import db, models
from app.api import api
from app.api.helpers import (
    code_to_airport,
    get_or_404,
    json_abort,
    role_required,
    str_to_date,
)
from app.forms import FlightForm
from flask_restful import Resource, reqparse, request


@api.resource("/flights")
class Flights(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("active", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]
        expand = args["expand"]
        active = args["active"]

        query = models.Flight.query

        # Only get active flights
        if active:
            query = query.filter(models.Flight.start <= dt.date.today())
            query = query.filter(models.Flight.end > dt.date.today())

        if search:
            query = query.msearch(f"{search}*")

        data = models.Flight.to_collection_dict(
            query, page, items_per_page, "api.flights", expand=expand, search=search
        )
        return data

    @role_required("admin")
    def post(self):
        form = FlightForm(data=request.json)
        if form.validate():
            flight = models.Flight()
            form.populate_obj(flight)
            db.session.add(flight)
            db.session.commit()
            db.session.refresh(flight)
            return flight.to_dict(), 201
        json_abort(400, message=form.errors)


@api.resource("/flights/<id>")
class Flight(Resource):
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        expand = args["expand"]

        flight = get_or_404(models.Flight, id)
        return flight.to_dict(expand=expand)

    @role_required("admin")
    def delete(self, id):
        flight = get_or_404(models.Flight, id)
        db.session.delete(flight)
        db.session.commit()
        return "", 204

    @role_required("admin")
    def patch(self, id):
        flight = get_or_404(models.Flight, id)
        form = FlightForm(data=request.json)
        if form.validate():
            form.populate_obj(flight)
            db.session.commit()
            db.session.refresh(flight)
            return flight.to_dict(), 200
        json_abort(400, message=form.errors)


@api.resource("/flights/<id>/tickets")
class FlightTickets(Resource):
    @role_required(["agent", "admin"])
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("date", type=str_to_date, location="args")

        args = parser.parse_args()
        expand = args["expand"]
        date = args["date"]

        flight = get_or_404(models.Flight, id)
        items = [
            ticket.to_dict(expand)
            for ticket in flight.tickets
            if ticket.transaction.departure_date == date
        ]
        
        return {
            "items": items,
            "_meta": {
                "total_items": len(items),
            },
        }
