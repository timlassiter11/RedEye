import json
import math
import random
from argparse import ArgumentParser
from datetime import date, datetime, time, timedelta, timezone
from getpass import getpass
from traceback import print_exc
from typing import List
from zoneinfo import ZoneInfo

import flask_migrate
import geopy.distance
from alive_progress import alive_it

from app import create_app, db, search
from app.models import Airplane, Airport, Flight, User
from config import Config


def create_db() -> None:
    print("Creating database.")
    flask_migrate.upgrade()


def create_user() -> None:
    print("Creating admin user.")
    email = input("Email: ")
    user: User = User.query.filter_by(email=email).first()
    # If the user doesn't exist create it
    if user is None:
        password = getpass()
        first_name = input("First Name: ")
        last_name = input("Last Name: ")
        user = User(
            first_name=first_name, last_name=last_name, email=email, role="admin"
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Successfully created admin user.")
    # Else just update the existing user
    else:
        print(f"User already exists... changing role from {user.role} to admin.")
        user.role = "admin"
        db.session.commit()
        print("Successfully updated user.")


def populate_airports() -> None:
    print("Populating database with airports from data/airports.json.")

    with open("data/airports.json") as f:
        data = f.read()
        json_data = json.loads(data)

    Airport.query.delete()
    search.delete_index(Airport)
    # Since both airplanes and flights rely
    # on airports we have to delete them.
    Airplane.query.delete()
    search.delete_index(Airplane)
    Flight.query.delete()
    search.delete_index(Flight)

    count = 0
    total_airports = len(json_data)
    for airport in alive_it(json_data):
        # Some airports are missing timezones.
        # This info is required so just ignore them.
        if not airport["tz"] or not airport["name"]:
            continue

        db.session.add(
            Airport(
                code=airport["code"],
                name=airport["name"],
                timezone=airport["tz"],
                latitude=airport["lat"],
                longitude=airport["lon"],
                city=airport["city"],
                state=airport["state"],
            )
        )
        count += 1
    print(f"Successfully added {count} airports out of {total_airports}")


def create_airplanes(count: int = 500) -> None:
    print(f"Populating database with {count} randomly generated airplanes")

    class AirplaneModel:
        def __init__(self, name, model, min_capacity, max_capacity, range) -> None:
            self.name = name
            self.model = model
            self.min_capacity = min_capacity
            self.max_capacity = max_capacity
            self.range = range

    # Create a list of common commercial plane models with their specifications
    models: List[AirplaneModel] = [
        AirplaneModel(
            "Boeing 737", "B737-800", min_capacity=189, max_capacity=189, range=1995
        ),
        AirplaneModel(
            "Airbus A320", "A320", min_capacity=140, max_capacity=180, range=3300
        ),
        AirplaneModel(
            "Boeing 757", "B757-200", min_capacity=200, max_capacity=200, range=3915
        ),
        AirplaneModel(
            "Boeing 777", "777-200ER", min_capacity=314, max_capacity=314, range=5845
        ),
    ]

    # Create a list of Red Eyes home airports. These will be the main
    # hubs for Red Eye and all planes will return here by the end of the day.
    home_airports = []
    home_airport_codes = ["DTW", "JFK", "SFO", "ORD", "IAD"]
    for code in home_airport_codes:
        airport = Airport.query.filter_by(code=code).first()
        if airport:
            home_airports.append(airport)

    Airplane.query.delete()
    search.delete_index(Airplane)
    # Since the flights rely on the planes
    # the flights have to be deleted too.
    Flight.query.delete()
    search.delete_index(Flight)
    registration_numbers = []
    for _ in alive_it(range(count)):
        # Start with a random base model
        model = random.choice(models)
        # Create a random capacity based off of the models min and max capacity
        capacity = random.randint(model.min_capacity, model.max_capacity)
        while True:
            # Aircraft registration numbers in the US start with an N
            # and can end with a two letter code representing the airline.
            # There can be up to 3 numbers in between for a range of 1 to 999.
            # We will use RE for Red Eye as the last two letters.
            number = random.randint(1, 999)
            registration_number = f"N{number}RE"
            # Make sure we don't have any repeating registration numbers.
            if registration_number not in registration_numbers:
                registration_numbers.append(registration_number)
                break

        airplane = Airplane(
            model_name=model.name,
            model_code=model.model,
            range=model.range,
            capacity=capacity,
            registration_number=registration_number,
            home_id=random.choice(home_airports).id,
        )
        db.session.add(airplane)
    print(f"Successfully created {count} airplanes.")


def create_flights(percentage: int = 90) -> None:
    print(
        f"Populating database with randomly generated flights using {percentage}% of the planes"
    )

    class FlightDetails:
        def __init__(self, departure: Airport, arrival: Airport) -> None:
            self.departure = departure
            self.arrival = arrival

            # Calculate the distance between the two airports.
            departure_coords = (departure.latitude, departure.longitude)
            arrival_coords = (arrival.latitude, arrival.longitude)
            self.distance = geopy.distance.geodesic(
                departure_coords, arrival_coords
            ).miles
            # If the plane can fly that far, use it. If not, start over.
            # Assume an average ground speed of 500nmph.
            travel_time = self.distance / 500
            hours = math.floor(travel_time)
            minutes = int((travel_time - hours) * 60)
            self.travel_time = timedelta(hours=hours, minutes=minutes)
            # Add a 30 minute buffer for takeoff and touchdown
            self.travel_time += timedelta(minutes=30)

            self.departure_tz = ZoneInfo(departure.timezone)
            self.arrival_tz = ZoneInfo(arrival.timezone)

        def reversed(self) -> "FlightDetails":
            return FlightDetails(self.arrival, self.departure)

    def get_cost(distance: float) -> float:
        # TODO: Figure out how to base cost on flight distance
        # Maybe also take plane capacity into account?
        return distance

    Flight.query.delete()
    search.delete_index(Flight)
    airports = Airport.query.all()
    planes = Airplane.query.all()
    # Grab a random list of planes to use based on the percentage given.
    # This allows us to have some spares that can be used as backups.
    total_flights = len(planes) * (percentage / 100)
    planes = random.choices(planes, k=int(total_flights))
    # A standard amount of time we want to set aside between
    # flights for deboarding, cleaning the plane, and boarding.
    boarding_buffer = timedelta(hours=1, minutes=30)

    flight_number = 1
    for plane in alive_it(planes):
        home_airport = Airport.query.get(plane.home_id)

        # Our earliest flights will always be between 5 and 7 am.
        hour = random.randint(5, 7)
        minute = random.choice([0, 15, 20, 30, 40, 45, 50])
        # Construst our time and make sure it's in the timezone of the home airport.
        departure_time = time(
            hour=hour, minute=minute, tzinfo=ZoneInfo(home_airport.timezone)
        )
        departure_dt = datetime.combine(date.today(), departure_time).astimezone(
            timezone.utc
        )
        # Datetime of the morning flight the next day.
        home_dt = departure_dt + timedelta(days=1)

        retrys = 10

        while True:
            flight_details = FlightDetails(home_airport, random.choice(airports))
            # If the airport is too close or the plane can't fly that far, start over and choose a new destination.
            if flight_details.distance < 500 or flight_details.distance > plane.range:
                continue

            # Make sure we have enough time to complete this flight and the return flight
            # before this planes usual morning flight the next day.
            total_flight_time = (flight_details.travel_time * 2) + (boarding_buffer * 2)
            remaining_time = home_dt - (departure_dt + total_flight_time)
            if remaining_time.total_seconds() < 0:
                # Just because this flight was too long doesn't mean
                # they all would be. Try again a few times and see
                # if we can find a flight that will fit in this time slot.
                if retrys:
                    retrys -= 1
                    continue
                break

            arrival_dt = departure_dt + flight_details.travel_time

            flight = Flight(
                number=f"{flight_number}",
                airplane_id=plane.id,
                departure_id=flight_details.departure.id,
                arrival_id=flight_details.arrival.id,
                departure_time=departure_dt.astimezone(
                    flight_details.departure_tz
                ).time(),
                arrival_time=arrival_dt.astimezone(flight_details.arrival_tz).time(),
                cost=get_cost(flight_details.distance),
            )
            db.session.add(flight)

            flight_number += 1
            flight_details = flight_details.reversed()
            # Add some buffer for the boarding process
            departure_dt = arrival_dt + boarding_buffer
            arrival_dt = departure_dt + flight_details.travel_time

            flight = Flight(
                number=f"{flight_number}",
                airplane_id=plane.id,
                departure_id=flight_details.departure.id,
                arrival_id=flight_details.arrival.id,
                departure_time=departure_dt.astimezone(
                    flight_details.departure_tz
                ).time(),
                arrival_time=arrival_dt.astimezone(flight_details.arrival_tz).time(),
                cost=get_cost(flight_details.distance),
            )
            db.session.add(flight)
            flight_number += 1
            departure_dt = arrival_dt + boarding_buffer


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Initialize the Red Eye database. If no arguments are given all functions will be run."
    )
    parser.add_argument(
        "-u", "--create-user", action="store_true", help="Create an admin user."
    )
    parser.add_argument(
        "-a",
        "--create-airports",
        action="store_true",
        help="Populate the database with airports from data/airports.json.",
    )
    parser.add_argument(
        "-b",
        "--create-airplanes",
        action="store_true",
        help="Populate the database with randomly generated airplanes.",
    )
    parser.add_argument(
        "-f",
        "--create-flights",
        action="store_true",
        help="Populate the database with randomly generated flights.",
    )
    parser.add_argument(
        "-t",
        "--total-planes",
        default=500,
        type=int,
        help="Total number of random planes to create.",
    )
    parser.add_argument(
        "-s",
        "--spare-percentage",
        default=10,
        type=int,
        help="Percentage of planes that should not be assigned flights.",
    )

    args = parser.parse_args()

    # If no args are given just do everything
    no_args = not (
        args.create_user
        or args.create_airports
        or args.create_airplanes
        or args.create_flights
    )

    config = Config
    # Dont' track modifications as this slows things down.
    # We will manually tell msearch to update the indexes at the end.
    config.SQLALCHEMY_TRACK_MODIFICATIONS = False
    app = create_app(config)

    with app.app_context():
        # Always create the database regardless if tables were dropped.
        # This ensures it's completely up to date and will do nothing if it is.
        create_db()

        if no_args or args.create_user:
            try:
                create_user()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("User creation cancelled.")
                else:
                    print_exc()

        if no_args or args.create_airports:
            try:
                populate_airports()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("Creating airports cancelled.")
                else:
                    print_exc()

        if no_args or args.create_airplanes:
            try:
                create_airplanes(count=args.total_planes)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("Creating airplanes cancelled")
                else:
                    print_exc()

        if no_args or args.create_flights:
            percentage = 100 - args.spare_percentage
            try:
                create_flights(percentage=percentage)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("Creating flights cancelled")
                else:
                    print_exc()

        print("Creating search indexes.")
        search.create_index()
