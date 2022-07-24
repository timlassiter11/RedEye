import json
import random
from typing import Dict, List, Union
import unittest

from flask_login import FlaskLoginClient
from app import create_app, db

from app.models import Admin, Agent, Airplane, Airport, Customer, User

DEFAULT_PASSWORD = "abc123"


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MSEARCH_ENABLE = True
    MSEARCH_BACKEND = "whoosh"
    MSEARCH_INDEX_NAME = "msearch_test"
    EMAIL_ADDR = "no-reply@workoutbuddy.app"


class FlaskTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.app.test_client_class = FlaskLoginClient
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()


def add_to_db(items):
    if isinstance(items, db.Model):
        items = [items]

    for item in items:
        db.session.add(item)

    db.session.commit()

    for item in items:
        db.session.refresh(item)


def create_users() -> Dict[str, User]:
    """Create users for each role. Returns a dict containing the created users."""
    admin = Admin(
        first_name="admin", last_name="user", email="adminuser@redeye.app"
    )
    admin.set_password(DEFAULT_PASSWORD)
    agent = Agent(
        first_name="agent", last_name="user", email="agentuser@redeye.app"
    )
    agent.set_password(DEFAULT_PASSWORD)
    customer = Customer(
        first_name="test", last_name="user", email="testuser@redeye.app"
    )
    customer.set_password(DEFAULT_PASSWORD)

    add_to_db([admin, agent, customer])
    return {"admin": admin, "agent": agent, "customer": customer}


def create_airports(count=5) -> Dict[str, Airport]:
    with open("data/airports.json") as f:
        data = f.read()
        json_data = json.loads(data)

    if count <= 0:
        count = len(json_data)

    index = 0
    airports = {}
    while index < count:
        airport = json_data[index]
        index += 1
        code = airport["code"]
        if code in airports or not airport["tz"] or not airport["name"]:
            continue

        airport = Airport(
            code=code,
            name=airport["name"],
            timezone=airport["tz"],
            latitude=airport["lat"],
            longitude=airport["lon"],
            city=airport["city"],
            state=airport["state"],
        )

        airports[code] = airport

    add_to_db(airports.values())

    return airports

def create_airplanes(count=5) -> List[Airplane]:
    airplanes = []
    for i in range(count):
        airplane = Airplane(
            registration_number=f"{i+1}",
            model_name="name",
            model_code="code",
            capacity=150,
            range=2000
        )
        db.session.add(airplane)
        airplanes.append(airplane)

    db.session.commit()
    for plane in airplanes:
        db.session.refresh(plane)

    return airplanes
