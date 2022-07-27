import datetime as dt

import pytz
from app import db
from app.models import (
    Airport,
    Flight,
    FlightCancellation,
    PurchaseTransaction,
    PurchasedTicket,
    TripItinerary,
    User,
)
from helpers import FlaskTestCase
from helpers import create_users, create_airports, create_airplanes, add_to_db


class TestUser(FlaskTestCase):
    def test_password(self):
        user = User()
        password = "abc&^%123"
        user.set_password(password)
        self.assertFalse(user.check_password(password[::-1]))
        self.assertTrue(user.check_password(password))

    def test_reset_token(self):
        user = User(email="testuser@redeye.app", first_name="test", last_name="user")
        user.set_password("abc123")
        add_to_db(user)
        token = user.get_reset_password_token()
        jwt_user = User.verify_reset_password_token(token[::-1])
        self.assertIsNone(jwt_user)
        jwt_user = User.verify_reset_password_token(token)
        self.assertEquals(user.id, jwt_user.id)

    def test_to_dict(self):
        user = User(email="testuser@redeye.app", first_name="test", last_name="user")
        user.set_password("abc123")
        data = user.to_dict()
        self.assertNotIn("password_hash", data)


class TestAirport(FlaskTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.airport1 = Airport(
            code="AAA",
            name="Test",
            timezone="Test",
            latitude=38.8280,
            longitude=-104.8270,
        )

        self.airport2 = Airport(
            code="AAB",
            name="Test",
            timezone="Test",
            latitude=36.8428,
            longitude=-76.0307,
        )

    def test_distance_to(self):
        d = self.airport1.distance_to(self.airport1)
        self.assertEquals(0, d)
        d = self.airport1.distance_to(self.airport2)
        # 1574.5208 is the known distance between the points
        self.assertAlmostEquals(1574.5208, d, places=4)
        # Make sure reversing the flight still gives us
        # a positive distance and not a negative.
        d = self.airport2.distance_to(self.airport1)
        self.assertAlmostEquals(1574.5208, d, places=4)

    def test_time_to(self):
        t = self.airport1.time_to(self.airport1)
        self.assertEquals(dt.timedelta(), t)
        t = self.airport1.time_to(self.airport2)
        # 3:08 is the known travel time between the two points
        self.assertEquals(dt.timedelta(hours=3, minutes=8), t)


class TestFlight(FlaskTestCase):
    def setUp(self) -> None:
        super().setUp()
        users = create_users()
        self.customer = users["customer"]
        self.agent = users["agent"]
        airports = create_airports(count=8)
        self.airports = list(airports.values())
        self.airplanes = create_airplanes()

    def test_is_cancelled(self):
        today = dt.date.today()
        plane = self.airplanes[0]
        flight = Flight(
            number="1",
            airplane_id=plane.id,
            departure_id=self.airports[0].id,
            arrival_id=self.airports[1].id,
            departure_time=dt.time(hour=5, minute=30),
            start=today,
            end=today,
        )
        add_to_db(flight)

        self.assertFalse(flight.is_cancelled(today))

        add_to_db(
            FlightCancellation(
                flight_id=flight.id, cancelled_by=self.agent.id, date=today
            )
        )

        self.assertTrue(flight.is_cancelled(today))

    def test_cancel(self):
        today = dt.date.today()
        plane = self.airplanes[0]
        flight = Flight(
            number="1",
            airplane_id=plane.id,
            departure_id=self.airports[0].id,
            arrival_id=self.airports[1].id,
            departure_time=dt.time(hour=5, minute=30),
            start=today,
            end=today,
        )

        add_to_db(flight)

        flight.cancel(today, self.agent.id)
        self.assertTrue(flight.is_cancelled(today))

    def test_available_seats(self):
        today = dt.date.today()
        plane = self.airplanes[0]
        flight = Flight(
            number="1",
            airplane_id=plane.id,
            departure_id=self.airports[0].id,
            arrival_id=self.airports[1].id,
            departure_time=dt.time(hour=5, minute=30),
            start=today,
            end=today,
        )

        add_to_db(flight)

        self.assertEquals(plane.capacity, flight.available_seats(today))

        transaction = PurchaseTransaction(email=self.customer.email)
        transaction.purchase_price = 500
        transaction.departure_date = today
        transaction.confirmation_number = transaction.generate_confirmation_number(
            "fake@teamred.app"
        )

        purchases = 5
        for _ in range(purchases):
            transaction.tickets.append(
                PurchasedTicket(
                    flight_id=flight.id,
                    first_name="Fake",
                    last_name="Person",
                    date_of_birth=dt.date.today(),
                    gender="no",
                    purchase_price=500,
                )
            )
        add_to_db(transaction)

        self.assertEquals(plane.capacity - purchases, flight.available_seats(today))


class TestTripItinerary(FlaskTestCase):
    def setUp(self) -> None:
        super().setUp()
        users = create_users()
        self.customer = users["customer"]
        self.agent = users["agent"]
        airports = create_airports(count=8)
        self.airports = list(airports.values())
        self.airplanes = create_airplanes()

    def test_layovers(self):
        today = dt.date.today()

        itinerary = TripItinerary(date=today)
        self.assertEquals(-1, itinerary.layovers)

        flight1 = Flight(
            number="1",
            airplane_id=self.airplanes[0].id,
            departure_id=self.airports[0].id,
            arrival_id=self.airports[1].id,
            departure_time=dt.time(hour=5, minute=30),
            start=today,
            end=today,
        )
        flight2 = Flight(
            number="2",
            airplane_id=self.airplanes[0].id,
            departure_id=self.airports[1].id,
            arrival_id=self.airports[2].id,
            departure_time=dt.time(hour=12, minute=10),
            start=today,
            end=today,
        )
        add_to_db([flight1, flight2])

        itinerary.add_flight(flight1)
        self.assertEquals(0, itinerary.layovers)
        itinerary.add_flight(flight2)
        self.assertEquals(1, itinerary.layovers)
        itinerary.pop_flight()
        self.assertEquals(0, itinerary.layovers)

    def test_total_time(self):
        today = dt.date.today()
        itinerary = TripItinerary(date=today)
        # With no flights it should be no time or an empty timedelta
        self.assertEquals(dt.timedelta(), itinerary.total_time)

        flight1_departure = dt.datetime.combine(
            today, dt.time(hour=5, minute=30), dt.timezone.utc
        )
        # Choose a time that's close to midnight to test rollover into the next day
        # TODO: Figure out a way to have the layover rollover as that's a more problematic scenario
        flight2_departure = dt.time(hour=23, minute=10)
        flight1 = Flight(
            number="1",
            airplane_id=self.airplanes[0].id,
            departure_id=self.airports[0].id,
            arrival_id=self.airports[1].id,
            departure_time=flight1_departure.time(),
            start=today,
            end=today,
        )
        flight2 = Flight(
            number="2",
            airplane_id=self.airplanes[0].id,
            departure_id=self.airports[1].id,
            arrival_id=self.airports[2].id,
            departure_time=flight2_departure,
            start=today,
            end=today,
        )
        add_to_db([flight1, flight2])

        itinerary.add_flight(flight1)
        # With only one flight it should be the same as that flights time
        self.assertEquals(flight1.flight_time, itinerary.total_time)

        # Calculate flight1's arrival so we can extract the date for flight2's departure
        flight1_arrival = flight1_departure + flight1.flight_time
        # Create flight2's departure time with the correct date
        flight2_departure = dt.datetime.combine(
            flight1_arrival.date(), flight2_departure, dt.timezone.utc
        )
        # Calculate flight2's arrival time
        flight2_arrival = flight2_departure + flight2.flight_time
        # Calculate total time by subtracting when we land vs when we left
        total_time = flight2_arrival - flight1_departure

        # Verify total time is still accurate after adding the second flight
        itinerary.add_flight(flight2)
        self.assertEquals(total_time, itinerary.total_time)
        # Verify total time is back to flight1's flight time
        itinerary.pop_flight()
        self.assertEquals(flight1.flight_time, itinerary.total_time)
        # Verify total time is back to nothing
        itinerary.pop_flight()
        self.assertEquals(dt.timedelta(), itinerary.total_time)
