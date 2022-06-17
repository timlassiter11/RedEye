import unittest

from flask import url_for

from app import create_app, db
from app.models import User
from flask_login import FlaskLoginClient

from helpers import TestConfig, create_users, DEFAULT_PASSWORD


class TestAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.app.test_client_class = FlaskLoginClient
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        db.create_all()
        users = create_users(db)
        self.admin_user = users["admin"]
        self.agent_user = users["agent"]
        self.normal_user = users["normal"]

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_register(self):
        user_data = {
            'first_name': 'test',
            'last_name': 'user',
            'email': 'testuser@redeye.app',
            'password': 'abc123',
            'password2': 'abc123'
        }

        # Make sure the GET method works
        with self.app.test_client() as client:
            response = client.get(url_for("auth.register"))
        self.assertEqual(200, response.status_code, "Invalid status code returned")

        # Make sure the POST method works and redirects to '/' on successful registration
        with self.app.test_client() as client:
            response = client.post(url_for("auth.register"), data=user_data)
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual("/", response.location, "Register redirected to incorrect location")

        # Make sure user was actually created in the db
        user: User = User.query.filter_by(email=user_data["email"]).first()
        self.assertIsNotNone(user, "Registered user not found in database")
        self.assertEqual(user_data["first_name"], user.first_name, "Invalid first name in database")
        self.assertEqual(user_data["last_name"], user.last_name, "Invalid last name in database")
        self.assertEqual(user_data["email"], user.email, "Invalid email in database")
        self.assertTrue(user.check_password(user_data["password"]), "Check password failed")

    def test_login(self):
        # Make sure the GET method works
        with self.app.test_client() as client:
            response = client.get(url_for("auth.login"))
        self.assertEqual(200, response.status_code, "Invalid status code returned")

        # Make sure the POST method works and redirects to '/' on successful login
        with self.app.test_client() as client:
            response = client.post(
                url_for("auth.login"),
                data={
                    "email": self.normal_user.email,
                    "password": DEFAULT_PASSWORD,
                },
            )
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual(url_for("main.home"), response.location, "Login redirected to incorrect location")

    def test_login_next(self):
        # Make sure the POST method works and redirects to '/' on successful login
        with self.app.test_client() as client:
            response = client.post(
                url_for("auth.login", next=url_for("admin.home")),
                data={
                    "email": self.admin_user.email,
                    "password": DEFAULT_PASSWORD,
                },
            )
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual(url_for("admin.home"), response.location, "Login redirected to incorrect location")

        # Make sure that the next parameter doesn't redirect to external pages
        with self.app.test_client() as client:
            response = client.post(
                url_for("auth.login", next="https://www.google.com"),
                data={
                    "email": self.admin_user.email,
                    "password": DEFAULT_PASSWORD,
                },
            )
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual(url_for("main.home"), response.location, "Login redirected to incorrect location")
