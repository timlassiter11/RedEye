from flask import Blueprint
from flask_restful import Api

bp = Blueprint("api", __name__)
api = Api(bp)

from app.api import routes

api.add_resource(routes.Airports, "/airports")
api.add_resource(routes.Airport, "/airports/<id>")
api.add_resource(routes.Airplanes, "/airplanes")
api.add_resource(routes.Airplane, "/airplanes/<id>")
api.add_resource(routes.Flights, "/flights")
api.add_resource(routes.Flight, "/flights/<id>")
