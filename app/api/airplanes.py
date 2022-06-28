from distutils.util import strtobool

from app import db, models
from app.api import api
from app.api.helpers import admin_required, get_or_404, json_abort
from app.forms import AirplaneForm
from flask_restful import Resource, reqparse, request
from sqlalchemy.exc import IntegrityError


@api.resource("/airplanes")
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


@api.resource("/airplanes/<id>")
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
