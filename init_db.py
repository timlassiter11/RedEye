import json
import random
from argparse import ArgumentParser
from datetime import date, datetime, time, timedelta, timezone
from getpass import getpass
from traceback import print_exc
from typing import List
from zoneinfo import ZoneInfo

import flask_migrate
from alive_progress import alive_it
from sqlalchemy.exc import IntegrityError

from config import Config
from app import create_app, db, search
from app.models import Admin, Airplane, Airport, Flight, PurchaseTransaction, PurchasedTicket


def create_db() -> None:
    print("Creating database.")
    flask_migrate.upgrade()


def create_user() -> None:
    print("Creating admin user. Press CTRL+c to cancel.")
    while True:
        email = input("Email: ")
        password = getpass()
        first_name = input("First Name: ")
        last_name = input("Last Name: ")
        user = Admin(
            first_name=first_name, last_name=last_name, email=email
        )
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            print("Successfully created admin user.")
            break
        except IntegrityError:
            print(f"User with that email already exists... Try again.")


def populate_airports(us_only: bool = False) -> None:
    print("Populating database with airports from data/airports.json.")

    with open("data/airports.json") as f:
        data = f.read()
        json_data = json.loads(data)

    PurchasedTicket.query.delete()
    PurchaseTransaction.query.delete()
    Flight.query.delete()
    Airport.query.delete()

    count = 0
    total_airports = len(json_data)
    for airport in alive_it(json_data):
        if us_only and airport["country"] != 'United States':
            continue

        # Some airports are missing timezones and names.
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

    # Since the flights rely on the planes
    # the flights have to be deleted.
    Flight.query.delete()
    Airplane.query.delete()

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
        )
        db.session.add(airplane)
    print(f"Successfully created {count} airplanes.")


def create_flights(percentage: int = 90) -> None:
    print(
        f"Populating database with randomly generated flights using {percentage}% of the planes"
    )

    PurchasedTicket.query.delete()
    Flight.query.delete()
    all_airports = list(Airport.query.all())
    airports = all_airports.copy()
    planes = Airplane.query.all()
    # Grab a random list of planes to use based on the percentage given.
    # This allows us to have some spares that can be used as backups.
    total_flights = len(planes) * (percentage / 100)

    planes = random.sample(planes, k=int(total_flights))
    # A standard amount of time we want to set aside between
    # flights for deboarding, cleaning the plane, and boarding.
    boarding_buffer = timedelta(hours=1, minutes=30)

    start_date = date.today()
    # Make all of our flights last about 6 months.
    end_date = (datetime.today() + timedelta(days=180)).date()

    # Create a list of Red Eyes home airports. These will be the main
    # hubs for Red Eye and all planes will return here by the end of the day.
    home_airports = []
    home_airport_codes = ["DTW", "JFK", "SFO", "ORD", "IAD"]
    for code in home_airport_codes:
        airport = Airport.query.filter_by(code=code).first()
        if airport:
            home_airports.append(airport)

    # Creates a list of pairs of airports covering all possible combinations.
    # This will allow us to create flights from every hub to every other hub
    # which will help with creating more available connecting flights.
    #home_flights = list(combinations(home_airports, 2))
    home_flights = [(a, b) for idx, a in enumerate(home_airports) for b in home_airports[idx + 1:]]

    flight_number = 1
    for plane in alive_it(planes):
        use_random = True
        if home_flights:
            home_airport, visiting_airport = home_flights.pop()
            miles = home_airport.distance_to(visiting_airport)
            if miles < plane.range:
                use_random = False
            else:
                home_flights.append((home_airport, visiting_airport))
                
        else:
            # Select a random home airport as our starting point
            home_airport = random.choice(home_airports)

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
        while retrys:
            # If we are out of home flights start randomly grabbing airports
            if use_random:
                if not airports:
                    airports = all_airports.copy()

                visiting_airport = random.sample(airports, 1)[0]
            
            distance = home_airport.distance_to(visiting_airport)
            # If the plane can't fly that far, start over and choose a new destination.
            if distance > plane.range:
                continue

            # Covers cases where the home and visiting airport are the same
            # and where airports would be less than a 30 minute flight away.
            if use_random and distance < 250:
                continue

            flight_time = home_airport.time_to(visiting_airport)
            # Make sure we have enough time to complete this flight and the return flight
            # before this planes usual morning flight the next day.
            total_flight_time = (flight_time * 2) + (boarding_buffer * 2)
            remaining_time = home_dt - (departure_dt + total_flight_time)
            if remaining_time.total_seconds() < 0:
                # Just because this flight was too long doesn't mean
                # they all would be. Try again a few times and see
                # if we can find a flight that will fit in this time slot.
                retrys -= 1
                continue


            arrival_dt = departure_dt + flight_time
            flight = Flight(
                number=f"{flight_number}",
                airplane_id=plane.id,
                departure_id=home_airport.id,
                arrival_id=visiting_airport.id,
                departure_time=departure_dt.time(),
                start=start_date,
                end=end_date
            )
            db.session.add(flight)
            flight_number += 1

            departure_dt = arrival_dt + boarding_buffer
            arrival_dt = departure_dt + flight_time
            flight = Flight(
                number=f"{flight_number}",
                airplane_id=plane.id,
                departure_id=visiting_airport.id,
                arrival_id=home_airport.id,
                departure_time=departure_dt.time(),
                start=start_date,
                end=end_date
            )
            db.session.add(flight)
            flight_number += 1
            # Set the departure time for the next loop.
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

    parser.add_argument(
        "--us-only",
        action="store_true",
        help="Only populate with US airports"
    )

    parser.add_argument(
        "-i",
        "--create-indexes",
        action="store_true",
        help='''Create search indexes. Search indexes are automatically created. 
        This is just for manually creating them.
        '''
    )

    args = parser.parse_args()

    # If no args are given just do everything
    no_args = not (
        args.create_user
        or args.create_airports
        or args.create_airplanes
        or args.create_flights
        or args.create_indexes
    )

    config = Config
    config.SQLALCHEMY_TRACK_MODIFICATIONS = False
    app = create_app()

    with app.app_context():
        # Always create the database regardless if tables were dropped.
        # This ensures it's completely up to date and will do nothing if it is.
        create_db()

        if no_args or args.create_user:
            try:
                create_user()
                db.session.commit()
            except (KeyboardInterrupt, Exception) as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("User creation cancelled.")
                else:
                    print_exc()

        if no_args or args.create_airports:
            try:
                populate_airports(args.us_only)
                db.session.commit()
            except (KeyboardInterrupt, Exception) as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("Creating airports cancelled.")
                else:
                    print_exc()

        if no_args or args.create_airplanes:
            try:
                create_airplanes(count=args.total_planes)
                db.session.commit()
            except (KeyboardInterrupt, Exception) as e:
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
            except (KeyboardInterrupt, Exception) as e:
                db.session.rollback()
                if isinstance(e, KeyboardInterrupt):
                    print("Creating flights cancelled")
                else:
                    print_exc()

        if no_args or args.create_indexes:
            print("Creating search indexes")
            search.create_index()
