import datetime as dt
from distutils.util import strtobool

from werkzeug.exceptions import HTTPException
from flask_login import current_user

from app import db, models
from app.api import api
from app.api.helpers import (
    get_or_404,
    json_abort,
    role_required,
    str_to_date,
)
from app.forms import FlightCancellationForm, FlightForm
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

        try:
            flight = get_or_404(models.Flight, id)
            return flight.to_dict(expand)
        except HTTPException:
            pass

        try:
            flight = models.Flight.query.filter_by(number=id).first()
            if flight:
                return flight.to_dict(expand)
        except ValueError:
            json_abort(404, message="Resource not found")

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


@api.resource("/flights/<id>/status")
class FlightStatus(Resource):
    @role_required(["agent", "admin"])
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("date", type=str_to_date, location="args")

        args = parser.parse_args()
        expand = args["expand"]
        date = args["date"]

        flight = get_or_404(models.Flight, id)
        cancellation = (
            models.FlightCancellation.query.filter_by(flight_id=flight.id)
            .filter_by(date=date)
            .first()
        )

        status = "active"
        if cancellation:
            status = "cancelled"

        query = (
            models.PurchasedTicket.query.filter_by(flight_id=flight.id)
            .join(models.PurchaseTransaction)
            .filter(models.PurchaseTransaction.departure_date == date)
            .filter(models.PurchasedTicket.refund_timestamp == None)
        )

        tickets = [ticket.to_dict(expand) for ticket in query.all()]

        return {"status": status, "tickets": tickets}


@api.resource("/flights/<id>/cancel")
class FlightCancellation(Resource):
    @role_required(["agent", "admin"])
    def post(self, id):
        flight: models.Flight = get_or_404(models.Flight, id)
        form = FlightCancellationForm(data=request.json)
        if form.validate():
            flight.cancel(form.date.data, current_user.id)
            return "", 204
