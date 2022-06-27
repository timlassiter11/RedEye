import math
import time
import datetime as dt
from typing import Any, Dict, List

import jwt
from flask import current_app, url_for
from flask_login import UserMixin
import pytz
from werkzeug.security import check_password_hash, generate_password_hash
import geopy.distance

from app import db, login


class PaginatedAPIMixin:
    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = dict(self.__dict__)
        # SQLAlchemy models contain an extra field that we don't want to expose.
        data.pop("_sa_instance_state", None)
        for key, value in data.items():
            if isinstance(value, dt.time):
                data[key] = value.strftime("%H:%M")
            if isinstance(value, dt.date):
                data[key] = value.strftime("%Y-%m-%d")

        if "id" in data:
            data["self"] = url_for(self.__endpoint__, id=data["id"])
            del data["id"]

        return data

    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        expand = kwargs.get("expand", False)
        resources = query.paginate(page, per_page, False)
        data = {
            "items": [item.to_dict(expand=expand) for item in resources.items],
            "_meta": {
                "page": page,
                "per_page": per_page,
                "total_pages": resources.pages,
                "total_items": resources.total,
            },
            "_links": {
                "self": url_for(endpoint, page=page, per_page=per_page, **kwargs),
                "next": url_for(endpoint, page=page + 1, per_page=per_page, **kwargs)
                if resources.has_next
                else None,
                "prev": url_for(endpoint, page=page - 1, per_page=per_page, **kwargs)
                if resources.has_prev
                else None,
            },
        }
        return data


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(10))

    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": role,
        "with_polymorphic": "*",
    }

    def __repr__(self):
        return f"<User {self.first_name} {self.last_name}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time.time() + expires_in},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token) -> "User":
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["reset_password"]
        except:
            return
        return User.query.get(id)


class Customer(User):
    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": "customer",
    }


class Agent(User):
    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": "agent",
    }


class Admin(User):
    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": "admin",
    }


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Airport(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.airport"
    __searchable__ = ["code", "name", "city", "state"]

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), index=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    timezone = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    def distance_to(self, other: "Airport") -> float:
        start_coords = (self.latitude, self.longitude)
        end_coords = (other.latitude, other.longitude)
        distance = geopy.distance.geodesic(start_coords, end_coords)
        return distance.miles

    def time_to(self, other: "Airport") -> dt.timedelta:
        # Assume an average ground speed of 500nmph.
        travel_time = self.distance_to(other) / 500
        hours = math.floor(travel_time)
        minutes = int((travel_time - hours) * 60)
        return dt.timedelta(hours=hours, minutes=minutes)


class Airplane(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.airplane"
    __searchable__ = ["registration_number", "model_name", "model_code"]

    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(120), index=True, unique=True)
    model_name = db.Column(db.String(120), nullable=False)
    model_code = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    range = db.Column(db.Integer, nullable=False)
    flights = db.relationship("Flight", backref="airplane")


class Flight(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.flight"
    __searchable__ = ["number"]

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(4), index=True)
    airplane_id = db.Column(db.Integer, db.ForeignKey("airplane.id"))
    departure_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    arrival_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    departure_time = db.Column(db.Time, nullable=False)
    start = db.Column(db.Date, nullable=False)
    end = db.Column(db.Date, nullable=False)

    departure_airport = db.relationship(
        "Airport", foreign_keys=[departure_id], backref="departures"
    )
    arrival_airport = db.relationship(
        "Airport", foreign_keys=[arrival_id], backref="arrivals"
    )

    @property
    def distance(self) -> float:
        if self.departure_airport is None or self.arrival_airport is None:
            return None

        return self.departure_airport.distance_to(self.arrival_airport)

    @property
    def flight_time(self) -> dt.timedelta:
        if self.departure_airport is None or self.arrival_airport is None:
            return None

        return self.departure_airport.time_to(self.arrival_airport)

    def cancel(self, date: dt.date, user_id: int) -> "FlightCancellation":
        cancellation = FlightCancellation(date=date, user_id=user_id, flight_id=self.id)
        db.session.add(cancellation)
        db.session.commit()
        db.session.refresh(cancellation)
        return cancellation

    @property
    def arrival_time(self) -> dt.time:
        departure_dt = dt.datetime.combine(dt.date.today(), self.departure_time)
        arrival_dt = departure_dt + self.flight_time
        return arrival_dt.time()

    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = super().to_dict()

        # We will replace these values with links to the resources
        # or the resource itself if expand is true.
        del data["airplane_id"]
        del data["departure_id"]
        del data["arrival_id"]

        data["flight_time"] = str(self.flight_time)
        data["arrival_time"] = self.arrival_time.strftime("%H:%M")

        if expand:
            data["airplane"] = self.airplane.to_dict()
            data["departure_airport"] = self.departure_airport.to_dict()
            data["arrival_airport"] = self.arrival_airport.to_dict()
        else:
            data["airplane"] = url_for(self.airplane.__endpoint__, id=self.airplane.id)
            data["departure_airport"] = url_for(
                self.departure_airport.__endpoint__, id=self.departure_id
            )
            data["arrival_airport"] = url_for(
                self.departure_airport.__endpoint__, id=self.arrival_id
            )

        return data


class FlightCancellation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey("flight.id"))
    cancelled_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    date = db.Column(db.Date, nullable=False)
    flight = db.relationship("Flight", backref="cancellations")


class TripItinerary:
    def __init__(self, date: dt.date, flights: List[Flight] = None) -> None:
        self._total_time = dt.timedelta()
        self._flights: List[Flight] = []
        self._date = date

        if flights:
            for flight in flights:
                self.add_flight(flight)

    def __len__(self):
        return len(self._flights)

    @property
    def flights(self) -> List[Flight]:
        return self._flights.copy()

    @property
    def layovers(self) -> int:
        if not self._flights:
            return None
        return len(self._flights) - 1

    @property
    def total_time(self) -> dt.timedelta:
        return self._total_time

    @property
    def departure_datetime(self) -> dt.datetime:
        if not self._flights:
            return None
        departure_dt = dt.datetime.combine(self._date, self.flights[0].departure_time, pytz.utc)
        return departure_dt

    @property
    def arrival_datetime(self) -> dt.datetime:
        if not self._flights:
            return None
        return self.departure_datetime + self.total_time

    @property
    def distance(self) -> float:
        if not self._flights:
            return None
        start = self.flights[0]
        end = self.flights[-1]
        return start.departure_airport.distance_to(end.arrival_airport)

    @property
    def cost(self) -> float:
        '''Calculates cost based on distance. Includes taxes.'''
        # https://taxfoundation.org/understanding-the-price-of-your-plane-ticket/#:~:text=The%20U.S.%20government%20charges%20an,(and%20almost%20all%20do).
        cost = self.distance
        # Excise tax
        cost += (cost * 0.075)
        # Flight segment tax of $4.5 per segment
        cost += (4.5 * len(self.flights))
        # September 11th tax
        cost += 5.6
        # Passenger facility charge (PFC)
        cost += (4.5 * len(self.flights) + 1)
        return round(cost, 2)

    def add_flight(self, flight: Flight) -> None:
        # This will be none if no flights have been added.
        last_arrival = self.arrival_datetime
        # If last_arrival is not None it means this isn't
        # the first flight and we need to add time for the layover.
        if last_arrival:
            # Base it on the date of the last arrival
            departure_dt = dt.datetime.combine(
                last_arrival.date(), flight.departure_time, pytz.utc
            )

            # Handle cases where the layover spans 
            # past midnight and into the next day.
            # TODO: Maybe add a test case for this issue?
            if departure_dt < last_arrival:
                departure_dt += dt.timedelta(days=1)

            # Add the layover to the total time
            self._total_time += departure_dt - last_arrival
        # Add the flight time
        self._total_time += flight.flight_time
        # Add the flight
        self._flights.append(flight)

    def pop_flight(self) -> Flight:
        # Remove flight
        flight = self._flights.pop()
        # If there are still more flights it means
        # we also need to remove the layover time.
        if self._flights:
            # This should still be the time the flight
            # being removed would have arrived at the final destination.
            last_arrival = self.arrival_datetime
            # This brings us back to right after the layover
            last_arrival -= flight.flight_time
            # This will be the new last flight.
            last_flight = self._flights[-1]
            new_arrival = dt.datetime.combine(last_arrival.date(), last_flight.arrival_time, pytz.utc)
            # Handle layover spanning past midnight
            if last_arrival < new_arrival:
                new_arrival -= dt.timedelta(days=1)
            
            self._total_time = new_arrival - self.departure_datetime
        else:
            # No flights means no flight time
            self._total_time = dt.timedelta()

        return flight

    def copy(self) -> "TripItinerary":
        itinerary = TripItinerary(self._date)
        itinerary._flights = self._flights.copy()
        itinerary._total_time = self._total_time
        return itinerary

    def to_dict(self, expand: bool = False):
        return {
            "cost": self.cost,
            "departure_datetime": self.departure_datetime.isoformat(),
            "arrival_datetime": self.arrival_datetime.isoformat(),
            "total_time": str(self.total_time),
            "layovers": self.layovers,
            "flights": [flight.to_dict(expand=expand) for flight in self.flights],
        }

    @staticmethod
    def search(
        departing_airport: int,
        final_airport: int,
        departure_date: dt.date,
        num_of_passengers: int = 1,
        max_layovers: int = 2,
        min_layover_time: dt.timedelta = dt.timedelta(minutes=45),
        max_layover_time: dt.timedelta = dt.timedelta(hours=5),
        previous_flight: "Flight" = None,
        current_itinerary: "TripItinerary" = None,
        trip_itinerarys: List[List["Flight"]] = None,
    ) -> List["TripItinerary"]:
        """Recursive function to create TripItineraries from departing_airport to final_airport.
        Final return value is a list of TripItineraries.
        """
        # If this is the first call to this function
        # we need to initialize the lists.
        if current_itinerary is None:
            current_itinerary = TripItinerary(departure_date)

        if trip_itinerarys is None:
            trip_itinerarys = []

        query = Flight.query

        if previous_flight:
            # If a previous flight was given, add it to the current path.
            current_itinerary.add_flight(previous_flight)
            # If the previous flight ended at our destination
            # that's the end of this path. Add it to the paths.
            if previous_flight.arrival_id == final_airport:
                trip_itinerarys.append(
                    current_itinerary.copy()
                )
                current_itinerary.pop_flight()
                return

            departure_dt = current_itinerary.arrival_datetime + min_layover_time

            departure_date = departure_dt.date()
            departure_time = departure_dt.time()
            # Filter out flights that depart before our departure_time
            query = query.filter(Flight.departure_time >= departure_time)

        # Find flights departing from our current airport.
        query = query.filter_by(departure_id=departing_airport)
        # Make sure flights fall within the departure date.
        query = query.filter(Flight.start <= departure_date)
        query = query.filter(departure_date <= Flight.end)
        # Make sure we avoid any cancelled flights.
        query = query.filter(
            ~Flight.cancellations.any(FlightCancellation.date == departure_date)
        )
        # If we are at our max layovers, only get flights
        # that go straight to our destination
        if current_itinerary.layovers == max_layovers - 1:
            query = query.filter_by(arrival_id=final_airport)

        # Make sure this flight doesn't backtrack to an airport we've already been to.
        prev_ids = [flight.departure_id for flight in current_itinerary.flights]
        query = query.filter(~Flight.arrival_id.in_(prev_ids))
        
        # TODO: Need to make sure all flights have enough seats for the number of passengers
        potential_flights = query.all()
        for flight in potential_flights:
            # Enforce a maximum layover length
            if previous_flight:
                start = dt.datetime.combine(
                    departure_date, previous_flight.arrival_time
                )
                end = dt.datetime.combine(departure_date, flight.departure_time)
                if end < start:
                    end += dt.timedelta(days=1)
                delta = end - start
                if delta > max_layover_time:
                    continue

            TripItinerary.search(
                departing_airport=flight.arrival_id,
                final_airport=final_airport,
                departure_date=departure_date,
                num_of_passengers=num_of_passengers,
                max_layovers=max_layovers,
                previous_flight=flight,
                current_itinerary=current_itinerary,
                trip_itinerarys=trip_itinerarys,
            )

        # When we exit this context it means we are done with this
        # branch of the "tree". Remove this flight from the path.
        if len(current_itinerary):
            current_itinerary.pop_flight()

        return trip_itinerarys


"""
class PurchasedFlight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'))
    purchased_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    assisted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    departure_date = db.Column(db.Date, nullable=False)
"""
