from app import db, models
from app.api import api
from app.api.helpers import admin_required, get_or_404, json_abort
from app.forms import AirportForm
from flask_restful import Resource, reqparse, request
from sqlalchemy.exc import IntegrityError


@api.resource("/airports")
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


@api.resource("/airports/<id>")
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
