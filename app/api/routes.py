from operator import attrgetter
from distutils.util import strtobool
from flask import request
from flask_restful import Resource, reqparse
from sqlalchemy.exc import IntegrityError

from app import db, models
from app.api.helpers import (
    code_to_airport,
    get_or_404,
    json_abort,
    admin_required,
    str_to_date,
)
from app.forms import AirplaneForm, AirportForm, FlightForm


class Airports(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = models.Airport.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.Airport.to_collection_dict(
            query, page, items_per_page, "api.airports", search=search
        )
        return data

    @admin_required
    def post(self):
        form = AirportForm(data=request.json)
        if form.validate():
            airport = models.Airport()
            form.populate_obj(airport)
            db.session.add(airport)
            try:
                db.session.commit()
                db.session.refresh(airport)
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409, message={"code": "An airport with this code already exists"}
                )
            return airport.to_dict(), 201
        json_abort(400, message=form.errors)


class Airport(Resource):
    def get(self, id):
        airport = get_or_404(models.Airport, id)
        return airport.to_dict()

    @admin_required
    def delete(self, id):
        airport = get_or_404(models.Airport, id)
        db.session.delete(airport)
        db.session.commit()
        return "", 204

    @admin_required
    def patch(self, id):
        airport: models.Airport = get_or_404(models.Airport, id)

        form = AirportForm(data=request.json)
        if form.validate():
            form.populate_obj(airport)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409, message={"code": "An airport with this code already exists"}
                )
            return airport.to_dict(), 201
        json_abort(400, message=form.errors)


class Airplanes(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument(
            "spares_only", type=strtobool, default=False, location="args"
        )

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]
        expand = args["expand"]
        spares = args["spares_only"]

        query = models.Airplane.query
        if search:
            query = query.msearch(f"{search}*")

        if spares:
            query = query.filter(~models.Airplane.flights.any())

        data = models.Airplane.to_collection_dict(
            query, page, items_per_page, "api.airplanes", expand=expand, search=search
        )
        return data

    @admin_required
    def post(self):
        form = AirplaneForm(data=request.json)
        if form.validate():
            airplane = models.Airplane()
            form.populate_obj(airplane)
            db.session.add(airplane)
            try:
                db.session.commit()
                db.session.refresh(airplane)
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409,
                    message={
                        "registration_number": "An airplane with this registration number already exists"
                    },
                )
            return airplane.to_dict(), 201
        json_abort(400, message=form.errors)


class Airplane(Resource):
    def get(self, id):
        expand = request.args.get("expand", False, type=strtobool)
        airplane = get_or_404(models.Airplane, id)
        return airplane.to_dict(expand=expand)

    @admin_required
    def delete(self, id):
        airplane = get_or_404(models.Airplane, id)
        db.session.delete(airplane)
        db.session.commit()
        return "", 204

    @admin_required
    def patch(self, id):
        airplane = get_or_404(models.Airplane, id)
        form = AirplaneForm(data=request.json)
        if form.validate():
            form.populate_obj(airplane)
            airplane.home_id = form.home_id
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409,
                    message={
                        "registration_number": "An airplane with this registration number already exists"
                    },
                )
            return airplane.to_dict(), 201
        json_abort(400, message=form.errors)


class Flights(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("departure_code", type=code_to_airport, location="args")
        parser.add_argument("arrival_code", type=code_to_airport, location="args")
        parser.add_argument("date", type=str_to_date, location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]
        expand = args["expand"]
        departure = args["departure_code"]
        arrival = args["arrival_code"]
        date = args["date"]

        query = models.Flight.query
        if search:
            query = query.msearch(f"{search}*")

        if departure:
            query = query.filter_by(departure_id=departure.id)

        if arrival:
            query = query.filter_by(arrival_id=arrival.id)

        if date:
            query = query.filter(models.Flight.start <= date).filter(
                date <= models.Flight.end
            )

        data = models.Flight.to_collection_dict(
            query, page, items_per_page, "api.flights", expand=expand, search=search
        )
        return data

    @admin_required
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


class Flight(Resource):
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        expand = args["expand"]

        flight = get_or_404(models.Flight, id)
        return flight.to_dict(expand=expand)

    @admin_required
    def delete(self, id):
        flight = get_or_404(models.Flight, id)
        db.session.delete(flight)
        db.session.commit()
        return "", 204

    @admin_required
    def patch(self, id):
        flight = get_or_404(models.Flight, id)
        form = FlightForm(data=request.json)
        if form.validate():
            form.populate_obj(flight)
            db.session.commit()
            return flight.to_dict(), 201
        json_abort(400, message=form.errors)


class FlightSearch(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "departure_code", type=code_to_airport, required=True, location="args"
        )
        parser.add_argument(
            "arrival_code", type=code_to_airport, required=True, location="args"
        )
        parser.add_argument(
            "departure_date", type=str_to_date, required=True, location="args"
        )
        parser.add_argument("num_of_passengers", type=int, default=1, location="args")
        parser.add_argument("max_layovers", type=int, default=3, location="args")
        parser.add_argument("min_layover_time", type=int, default=45, location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("limit", type=int, default=10, location="args")
        args = parser.parse_args()

        expand = args["expand"]
        departure = args["departure_code"]
        arrival = args["arrival_code"]
        departure_date = args["departure_date"]
        num_of_passengers = args["num_of_passengers"]
        max_layovers = args["max_layovers"]
        min_layover_time = args["min_layover_time"]
        limit = args["limit"]

        itineraries = models.TripItinerary.search(
            departing_airport=departure.id,
            final_airport=arrival.id,
            departure_date=departure_date,
            num_of_passengers=num_of_passengers,
            max_layovers=max_layovers,
            min_layover_time=min_layover_time,
        )
        # Sort the itineraries by the number of layovers, departure time, and total time.
        itineraries.sort(key=attrgetter("layovers", "departure_time", "total_time"))
        # Slice the list to limit the results.
        # Always do this after sorting so we get the best results.
        itineraries = itineraries[:limit]

        return {
            "items": [itinerary.to_dict(expand=expand) for itinerary in itineraries],
            "_meta": {
                "total_items": len(itineraries),
            },
        }
