from distutils.util import strtobool
from operator import attrgetter

from app import models
from app.api import api
from app.api.helpers import code_to_airport, str_to_date
from flask_restful import Resource, reqparse


@api.resource("/flights/search")
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
        parser.add_argument("max_layovers", type=int, default=2, location="args")
        parser.add_argument("min_layover_time", type=int, default=45, location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")
        parser.add_argument("limit", type=int, default=10, location="args")
        args = parser.parse_args()

        expand = args["expand"]
        departure = args["departure_code"]
        arrival = args["arrival_code"]
        # TODO: Departure date should always be after current date.
        # We can't check this on the server side though since the server might
        # be in a different timezone that is ahead of the client.
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
        itineraries.sort(
            key=attrgetter("layovers", "departure_datetime", "arrival_datetime")
        )
        # Slice the list to limit the results.
        # Always do this after sorting so we get the best results.
        itineraries = itineraries[:limit]

        return {
            "items": [itinerary.to_dict(expand=expand) for itinerary in itineraries],
            "_meta": {
                "total_items": len(itineraries),
            },
        }