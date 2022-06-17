import json
import random
from typing import Dict, List
import unittest

from flask_login import FlaskLoginClient
from app import create_app, db

from app.models import Airport, User

DEFAULT_PASSWORD = "abc123"


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MSEARCH_ENABLE = True
    MSEARCH_BACKEND = 'whoosh'
    MSEARCH_INDEX_NAME = "msearch_test"


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


def create_users(db) -> Dict[str, User]:
    """Create users for each role. Returns a dict containing the created users."""
    admin_user = User(
        first_name="admin", last_name="user", email="adminuser@redeye.app", role="admin"
    )
    admin_user.set_password(DEFAULT_PASSWORD)
    agent_user = User(
        first_name="agent", last_name="user", email="agentuser@redeye.app"
    )
    agent_user.set_password(DEFAULT_PASSWORD)
    normal_user = User(first_name="test", last_name="user", email="testuser@redeye.app")
    normal_user.set_password(DEFAULT_PASSWORD)

    db.session.add(admin_user)
    db.session.add(agent_user)
    db.session.add(normal_user)
    db.session.commit()
    db.session.refresh(admin_user)
    db.session.refresh(agent_user)
    db.session.refresh(normal_user)
    return {"admin": admin_user, "agent": agent_user, "normal": normal_user}


def create_airports(db, count=5) -> List[Airport]:
    with open("data/airports.json") as f:
        data = f.read()
        json_data = json.loads(data)

    airports = []
    airport_codes = []
    while count:
        airport = random.choice(json_data)
        if airport["code"] in airport_codes or not airport["tz"] or not airport["name"]:
            continue

        airport = Airport(
            code=airport["code"],
            name=airport["name"],
            timezone=airport["tz"],
            latitude=airport["lat"],
            longitude=airport["lon"],
            city=airport["city"],
            state=airport["state"],
        )

        db.session.add(airport)
        airports.append(airport)
        count -= 1

    db.session.commit()
    for airport in airports:
        db.session.refresh(airport)

    return airports