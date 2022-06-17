import unittest

from flask import url_for

from app import db
from app.models import User

from helpers import FlaskTestCase, DEFAULT_PASSWORD, create_users


class TestAuth(FlaskTestCase):
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
        users = create_users(db)
        user = users['normal']
        # Make sure the GET method works
        with self.app.test_client() as client:
            response = client.get(url_for("auth.login"))
        self.assertEqual(200, response.status_code, "Invalid status code returned")

        # Make sure the POST method works and redirects to '/' on successful login
        with self.app.test_client() as client:
            response = client.post(
                url_for("auth.login"),
                data={
                    "email": user.email,
                    "password": DEFAULT_PASSWORD,
                },
            )
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual(url_for("main.home"), response.location, "Login redirected to incorrect location")

    def test_login_next(self):
        users = create_users(db)
        user = users['admin']
        # Make sure the POST method works and redirects to '/' on successful login
        with self.app.test_client() as client:
            response = client.post(
                url_for("auth.login", next=url_for("admin.home")),
                data={
                    "email": user.email,
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
                    "email": user.email,
                    "password": DEFAULT_PASSWORD,
                },
            )
        self.assertEqual(302, response.status_code, "Invalid status code returned")
        self.assertEqual(url_for("main.home"), response.location, "Login redirected to incorrect location")
