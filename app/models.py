import datetime as dt
import math
import random
import string
import time
import uuid
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import geopy.distance
import jwt
import pytz
from flask import current_app, url_for
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, and_, desc, func, or_
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login
from app.email import send_bulk_email
from app.helpers import calculate_taxes


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


class User(UserMixin, PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.user"
    __searchable__ = ["email", "first_name", "last_name"]

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

    def purchases(self, start: dt.date = None, end: dt.date = None):
        """Get all of the users purchases starting from start (inclusive) and ending with end (exclusive)."""

        query = PurchaseTransaction.query.filter_by(email=self.email)

        if start is not None:
            query = query.filter(PurchaseTransaction.departure_date >= start)

        if end is not None:
            query = query.filter(PurchaseTransaction.departure_date < end)

        query = query.order_by(PurchaseTransaction.departure_date)
        return list(query.all())

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

    def to_dict(self, **kwargs):
        data = super().to_dict(**kwargs)
        del data["password_hash"]
        return data


class Customer(User):
    __endpoint__ = "api.customer"

    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "customer",
    }


class Agent(User):
    __endpoint__ = "api.agent"

    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "agent",
    }

    def _sales_from_query(self, query) -> List[Dict]:
        return [
            {"date": row["date"], "sales": round(row["sales"], 2)}
            for row in query.all()
        ]

    def sales_by_date(self, start: dt.date, end: dt.date) -> List[Dict]:

        date_col = func.date(PurchaseTransaction.purchase_timestamp).label("date")

        query = (
            db.session.query(
                PurchaseTransaction.id,
                func.sum(PurchaseTransaction.base_fare).label("sales"),
                date_col,
            )
            .filter(date_col >= start)
            .filter(date_col <= end)
            .group_by("date")
            .order_by("date")
        )

        return self._sales_from_query(query)

    def sales_by_month(self, start: dt.date, end: dt.date) -> List[Dict]:
        month_col = func.month(PurchaseTransaction.purchase_timestamp).label("month")
        year_col = func.year(PurchaseTransaction.purchase_timestamp).label("year")
        date_col = func.str_to_date(
            func.concat(year_col, "-", month_col, "-", "01"), "%Y-%m-%d"
        ).label("date")

        query = (
            db.session.query(
                PurchaseTransaction.id,
                func.sum(PurchaseTransaction.base_fare).label("sales"),
                date_col,
            )
            .filter(date_col >= start)
            .filter(date_col <= end)
            .group_by("date")
            .order_by("date")
        )

        return self._sales_from_query(query)


class Admin(User):
    __endpoint__ = "api.admin"

    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

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
    departure_time = db.Column(db.Time, nullable=False, index=True)
    start = db.Column(db.Date, nullable=False, index=True)
    end = db.Column(db.Date, nullable=False, index=True)

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

    @property
    def arrival_time(self) -> dt.time:
        departure_dt = dt.datetime.combine(dt.date.today(), self.departure_time)
        arrival_dt = departure_dt + self.flight_time
        return arrival_dt.time()

    def cost(self, date: dt.date) -> float:
        # TODO: Figure out better pricing model.
        # Maybe base it on date?
        # Weekends more expenive?
        # Have the ability to put surge charges in the DB?
        return round(self.distance * 0.2, 2)

    def is_cancelled(self, date: dt.date) -> bool:
        cancellation = (
            FlightCancellation.query.filter_by(flight_id=self.id)
            .filter_by(date=date)
            .first()
        )
        return cancellation is not None

    def cancel(self, date: dt.date, user_id: int) -> "FlightCancellation":
        if date < self.start or date > self.end:
            raise ValueError("date must be between start and end")

        cancellation = FlightCancellation(
            date=date, cancelled_by=user_id, flight_id=self.id
        )
        db.session.add(cancellation)

        # Refund all of the tickets
        tickets = (
            PurchasedTicket.query.filter_by(flight_id=self.id)
            .join(PurchaseTransaction)
            .filter(PurchaseTransaction.departure_date == date)
            .filter(PurchasedTicket.refund_timestamp == None)
            .all()
        )

        emails = []
        data = []
        for ticket in tickets:
            ticket.refund_timestamp = func.now()
            ticket.refunded_by = user_id

            email = ticket.transaction.email
            if email not in emails:
                emails.append(email)
                data.append({"transaction": ticket.transaction})

        # TODO: Send emails out to all of the transaction emails
        # send_bulk_email('Flight Cancellation', ('RedEye', current_app.config['EMAIL_ADDR']), email, data, )

        db.session.commit()
        db.session.refresh(cancellation)
        return cancellation

    def available_seats(self, date: dt.date) -> int:
        if date < self.start or date > self.end:
            raise ValueError("date must be between start and end")

        if self.is_cancelled(date):
            return 0

        capacity = self.airplane.capacity
        used = (
            PurchasedTicket.query.filter_by(flight_id=self.id)
            .outerjoin(
                PurchaseTransaction,
                PurchaseTransaction.id == PurchasedTicket.transaction_id,
            )
            .filter(PurchaseTransaction.departure_date == date)
            .count()
        )
        return capacity - used

    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = super().to_dict()

        # We will replace these values with links to the resources
        # or the resource itself if expand is true.
        del data["airplane_id"]
        del data["departure_id"]
        del data["arrival_id"]

        data["flight_time"] = str(self.flight_time)
        data["arrival_time"] = self.arrival_time.strftime("%H:%M")
        data["status"] = url_for("api.flightstatus", id=self.id)
        data["cancel"] = url_for("api.flightcancellation", id=self.id)

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
                self.arrival_airport.__endpoint__, id=self.arrival_id
            )

        return data


class FlightCancellation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    flight_id = db.Column(db.Integer, db.ForeignKey("flight.id"))
    cancelled_by = db.Column(db.Integer, db.ForeignKey("agent.id"))
    date = db.Column(db.Date, nullable=False)

    flight = db.relationship("Flight", backref="cancellations")


class PurchaseTransaction(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.purchase"
    __searchable__ = ["email", "confirmation_number"]

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), index=True, nullable=False)
    confirmation_number = db.Column(db.String(6), index=True, nullable=False)
    departure_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    destination_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    departure_date = db.Column(db.Date, nullable=False)
    purchase_timestamp = db.Column(
        db.DateTime, nullable=False, server_default=func.now()
    )
    purchase_price = db.Column(db.Float, nullable=False)
    assisted_by = db.Column(db.Integer, db.ForeignKey("agent.id"))

    agent = db.relationship("Agent", backref="sales")
    departure_airport = db.relationship("Airport", foreign_keys=[departure_id])
    destination_airport = db.relationship("Airport", foreign_keys=[destination_id])

    __table_args__ = (UniqueConstraint("email", "confirmation_number", name="_pnr"),)

    @property
    def base_fare(self) -> float:
        total = 0
        for ticket in self.tickets:
            total += ticket.purchase_price
        return round(total, 2)

    @property
    def taxes(self) -> float:
        return round(self.purchase_price - self.base_fare, 2)

    @property
    def refund_amount(self) -> float:
        amount = 0
        taxes = self.taxes
        for ticket in self.tickets:
            if ticket.refund_timestamp:
                amount += ticket.purchase_price
                # Return a percentage of the taxes
                amount += taxes * 1 / len(self.tickets)

        return amount

    @property
    def refunded(self) -> bool:
        """Returns true if all of the tickets for this purchase have been refunded"""
        return all(ticket.refund_timestamp is not None for ticket in self.tickets)

    @property
    def flights(self) -> List[Flight]:
        query = (
            PurchasedTicket.query.filter_by(transaction_id=self.id)
            .group_by(PurchasedTicket.flight_id)
            .order_by(PurchasedTicket.id)
        )
        return [ticket.flight for ticket in query.all()]

    @property
    def total_passengers(self) -> int:
        query = PurchasedTicket.query.filter_by(transaction_id=self.id).group_by(
            PurchasedTicket.first_name,
            PurchasedTicket.middle_name,
            PurchasedTicket.last_name,
        )
        return query.count()

    @staticmethod
    def generate_confirmation_number(email: str):
        while True:
            cn = "".join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits)
                for _ in range(6)
            )
            exists = PurchaseTransaction.query.filter(
                and_(PurchaseTransaction.email == email),
                PurchaseTransaction.confirmation_number == cn,
            ).count()
            if not exists:
                return cn

    @property
    def num_of_passengers(self) -> int:
        query = (
            db.session.query(func.count(PurchasedTicket.id))
            .filter(PurchasedTicket.transaction_id == self.id)
            .group_by(PurchasedTicket.flight_id)
        )
        return query.first()[0]

    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = super().to_dict(expand)

        del data["departure_id"]
        del data["destination_id"]
        del data["assisted_by"]

        data["taxes"] = self.taxes
        data["base_fare"] = self.base_fare

        if expand:
            data["departure_airport"] = self.departure_airport.to_dict()
            data["destination_airport"] = self.destination_airport.to_dict()
            if self.agent:
                data["agent"] = f"{self.agent.first_name} {self.agent.last_name}"
        else:
            data["departure_airport"] = url_for(
                self.departure_airport.__endpoint__, id=self.departure_id
            )
            data["destination_airport"] = url_for(
                self.destination_airport.__endpoint__, id=self.destination_id
            )
            if self.agent:
                data["agent"] = url_for("api.agents", id=self.assisted_by)

        data["tickets"] = [ticket.to_dict(expand) for ticket in self.tickets]
        return data


class PurchasedTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    transaction_id = db.Column(
        db.Integer, db.ForeignKey("purchase_transaction.id"), nullable=False
    )
    flight_id = db.Column(db.Integer, db.ForeignKey("flight.id"), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    middle_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    refund_timestamp = db.Column(db.DateTime)
    refunded_by = db.Column(db.Integer, db.ForeignKey("agent.id"))

    transaction = db.relationship("PurchaseTransaction", backref="tickets")
    flight = db.relationship("Flight", backref="tickets")
    agent = db.relationship("Agent", backref="refunds")

    def to_dict(self, expand=False):
        refund = self.refund_timestamp
        if refund:
            refund = refund.isoformat()

        agent = None
        if self.agent:
            agent = f"{self.agent.first_name} {self.agent.last_name}"

        return {
            "self": url_for("api.purchase", id=self.id),
            "flight": self.flight.to_dict(expand)
            if expand
            else url_for("api.flight", id=self.flight_id),
            "transaction": url_for("api.purchase", id=self.transaction_id),
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.strftime("%Y-%m-%d"),
            "gender": self.gender,
            "purchase_price": self.purchase_price,
            "refund_timestamp": refund,
            "refunded_by": agent,
        }


class TripFlight:
    """Holds a flight with it's accompanying departure date.
    This is needed for itineraries as they could span into the next day.
    """

    def __init__(self, flight: Flight, date: dt.date):
        self.flight = flight
        self.date = date

    @property
    def departure_datetime(self) -> dt.datetime:
        return dt.datetime.combine(self.date, self.flight.departure_time, pytz.utc)

    @property
    def arrival_datetime(self) -> dt.datetime:
        return self.departure_datetime + self.flight.flight_time

    @property
    def is_cancelled(self) -> bool:
        return self.flight.is_cancelled(self.date)

    def to_dict(self, expand=False):
        data = self.flight.to_dict(expand)
        data["departure_datetime"] = self.departure_datetime.isoformat()
        data["arrival_datetime"] = self.arrival_datetime.isoformat()
        return data


class TripItinerary:
    def __init__(
        self,
        date: dt.date,
        flights: List[Flight] = None,
    ) -> None:
        self.id = uuid.uuid4().hex
        self._total_time = dt.timedelta()
        self._flights: List[TripFlight] = []
        self._date = date

        if flights:
            for flight in flights:
                self.add_flight(flight)

    def __len__(self):
        return len(self._flights)

    @property
    def flights(self) -> List[TripFlight]:
        return self._flights.copy()

    @property
    def layovers(self) -> int:
        return len(self._flights) - 1

    @property
    def total_time(self) -> dt.timedelta:
        return self._total_time

    @property
    def departure_airport(self) -> Airport:
        if not self._flights:
            return None
        return self._flights[0].flight.departure_airport

    @property
    def arrival_airport(self) -> Airport:
        if not self._flights:
            return None
        return self._flights[-1].flight.arrival_airport

    @property
    def departure_datetime(self) -> dt.datetime:
        if not self._flights:
            return None

        departure_flight = self._flights[0]
        return dt.datetime.combine(
            departure_flight.date, departure_flight.flight.departure_time, pytz.utc
        )

    @property
    def arrival_datetime(self) -> dt.datetime:
        if not self._flights:
            return None
        return self.departure_datetime + self.total_time

    @property
    def distance(self) -> float:
        # TODO: Should this be distance from start to end or
        # total distance of all flights? It's ambiguous right now.
        if not self._flights:
            return None
        start = self._flights[0].flight
        end = self._flights[-1].flight
        return start.departure_airport.distance_to(end.arrival_airport)

    @property
    def cost(self) -> float:
        return round(self.base_fare + self.taxes, 2)

    @property
    def base_fare(self):
        cost = 0
        for flight in self._flights:
            cost += flight.flight.cost(self._date)
        return cost

    @property
    def taxes(self):
        return calculate_taxes(self.base_fare, len(self._flights))

    def add_flight(self, flight: Flight) -> None:
        # TODO: Should we check to make sure we can add this flight?
        # As in check to make sure the departing airport is the same
        # as the last arrival airport and that the departure time is
        # after the last arrival time?

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
            if departure_dt < last_arrival:
                departure_dt += dt.timedelta(days=1)

            # Add the layover to the total time
            self._total_time += departure_dt - last_arrival
        else:
            departure_dt = dt.datetime.combine(
                self._date, flight.departure_time, pytz.utc
            )

        # Add the flight time
        self._total_time += flight.flight_time
        # Add the flight
        self._flights.append(TripFlight(flight, departure_dt.date()))

    def pop_flight(self) -> Flight:
        # Remove flight
        flight = self._flights.pop().flight
        # If there are still more flights it means
        # we also need to remove the layover time.
        if self._flights:
            # This should still be the time the flight
            # being removed would have arrived at the final destination.
            last_arrival = self.arrival_datetime
            # This brings us back to right after the layover
            last_arrival -= flight.flight_time
            # This will be the new last flight.
            last_flight = self._flights[-1].flight
            new_arrival = dt.datetime.combine(
                last_arrival.date(), last_flight.arrival_time, pytz.utc
            )
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

    def to_dict(self, expand: bool = False, utc: bool = False):
        departure_dt = self.departure_datetime
        arrival_dt = self.arrival_datetime

        if not utc:
            departure_dt = departure_dt.astimezone(
                ZoneInfo(self.departure_airport.timezone)
            )
            arrival_dt = arrival_dt.astimezone(ZoneInfo(self.arrival_airport.timezone))

        return {
            "id": self.id,
            "cost": self.cost,
            "base_fare": self.base_fare,
            "taxes": self.taxes,
            "departure_airport": self._flights[0].flight.departure_airport.to_dict(),
            "arrival_airport": self._flights[-1].flight.arrival_airport.to_dict(),
            "departure_datetime": departure_dt.isoformat(),
            "arrival_datetime": arrival_dt.isoformat(),
            "total_time": str(self.total_time),
            "layovers": self.layovers,
            "flights": [flight.to_dict(expand=expand) for flight in self._flights],
        }

    @staticmethod
    def search(
        departing_airport: int,
        final_airport: int,
        departure_date: dt.date,
        num_of_passengers: int = 1,
        max_layovers: int = 2,
        limit: int = 10,
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
                trip_itinerarys.append(current_itinerary.copy())
                current_itinerary.pop_flight()
                return

            departure_dt = current_itinerary.arrival_datetime + min_layover_time

            departure_date = departure_dt.date()
            departure_time = departure_dt.time()
            # Filter out flights that depart before our departure_time
            query = query.filter(Flight.departure_time >= departure_time)
        else:
            # Filter out flights that have already taken off
            # if they are looking for same day flights.
            if departure_date == dt.date.today():
                # Add 45 minutes to filter out flights that are already boarding.
                now = dt.datetime.utcnow() + dt.timedelta(minutes=45)
                query = query.filter(Flight.departure_time > now.time())

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
        prev_ids = [flight.flight.departure_id for flight in current_itinerary._flights]
        query = query.filter(~Flight.arrival_id.in_(prev_ids))

        # Create a subquery which counts the total number of tickets sold for each flight
        subquery = (
            db.session.query(
                PurchasedTicket.flight_id,
                PurchaseTransaction.departure_date,
                func.count(PurchasedTicket.id).label("purchased_tickets"),
            )
            .join(
                PurchaseTransaction,
                PurchasedTicket.transaction_id == PurchaseTransaction.id,
            )
            .filter(PurchaseTransaction.departure_date == departure_date)
            .filter(PurchasedTicket.refund_timestamp == None)
            .group_by(PurchasedTicket.flight_id)
            .group_by(PurchaseTransaction.departure_date)
            .subquery()
        )
        # Outer join ensures that results without purchased tickets are still retrieved
        query = query.outerjoin(subquery, Flight.id == subquery.c.flight_id)
        # We need to know the capacity of the plane
        query = query.join(Airplane)
        # Filter out flights without enough available seats or that have no tickets sold (purchased_tickets == None)
        query = query.filter(
            or_(
                (Airplane.capacity - subquery.c.purchased_tickets) >= num_of_passengers,
                subquery.c.purchased_tickets == None,
            )
        )

        # Prioritize direct flights by placing them first.
        query = query.order_by(desc(func.field(Flight.arrival_id, final_airport)))
        # Then order by departure time.
        query = query.order_by(desc(Flight.departure_time))

        potential_flights: List[Flight] = query.all()
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

            if len(trip_itinerarys) >= limit:
                break

        # When we exit this context it means we are done with this
        # branch of the "tree". Remove this flight from the path.
        if len(current_itinerary):
            current_itinerary.pop_flight()

        return trip_itinerarys
