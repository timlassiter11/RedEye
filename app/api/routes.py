from distutils.util import strtobool
from flask import jsonify, request
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from app import db, models
from app.api.helpers import get_or_404, json_abort, admin_required
from app.forms import AirplaneForm, AirportForm, FlightForm


class Airports(Resource):
    def get(self):
        items_per_page = request.args.get("per_page", 25, type=int)
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "", type=str)

        query = models.Airport.query
        if search:
            query = query.msearch(search)

        data = models.Airport.to_collection_dict(
            query, page, items_per_page, "api.airports", search=search
        )
        return jsonify(data)

    @admin_required
    def post(self):
        form = AirportForm(data=request.json)
        if form.validate():
            airport = models.Airport()
            form.populate_obj(airport)
            db.session.add(airport)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409, errors={"code": "An airport with this code already exists"}
                )
            return jsonify(airport.to_dict()), 201
        json_abort(400, errors=form.errors)


class Airport(Resource):
    def get(self, id):
        airport = get_or_404(models.Airport, id)
        return jsonify(airport.to_dict())

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
                    409, errors={"code": "An airport with this code already exists"}
                )
            return jsonify(airport.to_dict()), 201
        json_abort(400, errors=form.errors)


class Airplanes(Resource):
    def get(self):
        items_per_page = request.args.get("per_page", 25, type=int)
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "", type=str)
        spares = request.args.get("spares", False, type=strtobool)
        expand = request.args.get("expand", False, type=strtobool)

        query = models.Airplane.query
        if search:
            query = query.msearch(f"*{search}*")

        if spares:
            query = query.filter(~models.Airplane.flights.any())

        data = models.Airplane.to_collection_dict(
            query, page, items_per_page, "api.airplanes", expand=expand, search=search
        )
        return jsonify(data)

    @admin_required
    def post(self):
        form = AirplaneForm(data=request.json)
        if form.validate():
            airplane = models.Airplane()
            form.populate_obj(airplane)
            db.session.add(airplane)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                json_abort(
                    409,
                    errors={
                        "registration_number": "An airplane with this registration number already exists"
                    },
                )
            return jsonify(airplane.to_dict()), 201
        json_abort(400, errors=form.errors)


class Airplane(Resource):
    def get(self, id):
        expand = request.args.get("expand", False, type=strtobool)
        airplane = get_or_404(models.Airplane, id)
        return jsonify(airplane.to_dict(expand=expand))

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
                    errors={
                        "registration_number": "An airplane with this registration number already exists"
                    },
                )
            return jsonify(airplane.to_dict()), 201
        json_abort(400, errors=form.errors)


class Flights(Resource):
    def get(self):
        items_per_page = request.args.get("per_page", 25, type=int)
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "", type=str)
        expand = request.args.get("expand", False, type=strtobool)

        query = models.Flight.query
        if search:
            query = query.msearch(search)

        data = models.Flight.to_collection_dict(
            query, page, items_per_page, "api.flights", expand=expand, search=search
        )
        return jsonify(data)

    @admin_required
    def post(self):
        form = FlightForm(data=request.json)
        if form.validate():
            flight = models.Flight()
            form.populate_obj(flight)
            db.session.add(flight)
            db.session.commit()
            return jsonify(flight.to_dict()), 201
        json_abort(400, errors=form.errors)


class Flight(Resource):
    def get(self, id):
        expand = request.args.get("expand", False, type=strtobool)
        flight = get_or_404(models.Flight, id)
        return jsonify(flight.to_dict(expand=expand))

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
            return jsonify(flight.to_dict()), 201
        json_abort(400, errors=form.errors)
