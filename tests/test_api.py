import unittest

from flask import url_for
from flask_login import FlaskLoginClient
from werkzeug.test import TestResponse

from app import create_app, db
from app.models import Airport
from helpers import create_users, TestConfig


class ApiTestCase(unittest.TestCase):
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

    def assertApiResponse(self, response: "TestResponse", expected_status: int = 200):
        self.assertEqual(
            expected_status, response.status_code, "Invalid status code returned"
        )
        self.assertTrue(response.is_json, "Invalid response returned")

    def assertPaginatedResponse(
        self,
        response: "TestResponse",
        expected_status: int = 200,
        expected_page: int = None,
        expected_per_page: int = None,
        expected_total_pages: int = None,
        expected_total_items: int = None,
    ):
        """Asserts that a paginated api response contains all of the expected fields."""
        self.assertApiResponse(response, expected_status)

        self.assertIn("_meta", response.json, "Missing _meta in api response")
        meta = response.json['_meta']
        self.assertIn("page", meta, "Missing _meta.page in api response")
        self.assertIn("per_page", meta, "Missing _meta.per_page in api response")
        self.assertIn("total_pages", meta, "Missing _meta.total_pages in api response")
        self.assertIn("total_items", meta, "Missing _meta.total_items in api response")

        self.assertIn("_links", response.json, "Missing _links in api resonse.")
        links = response.json['_links']
        self.assertIn("self", links, "Missing _links.self in api response")
        self.assertIn("next", links, "Missing _links.next in api response")
        self.assertIn("prev", links, "Missing _links.prev in api response")

        self.assertIn("items", response.json, "Missing items in api response.")
        items = response.json['items']

        if expected_page is not None:
            self.assertEqual(expected_page, meta["page"], "Incorrect value for _meta.page in api response")
        if expected_per_page is not None:
            self.assertEqual(expected_per_page, meta["per_page"], "Incorrect value for _meta.per_page in api response")
        if expected_total_pages is not None:
            self.assertEqual(expected_total_pages, meta["total_pages"], "Incorrect value for _meta.total_pages in api response")
        if expected_total_items is not None:
            self.assertEqual(expected_total_items, meta["total_items"], "Incorrect value for _meta.total_items in api response")
            self.assertEqual(expected_total_items, len(items), "Incorrect number of items in api response")


class TestAirports(ApiTestCase):
    def test_get_airports(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154,
        )
        # Test to make sure everything works with no airports
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports"))

        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=0, expected_total_items=0)
        db.session.add(airport)
        db.session.commit()
        # Test to make sure everything works with a single airport
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports"))

        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=1, expected_total_items=1)
        airport_data = response.json["items"][0]
        self.assertDictEqual(
            airport.to_dict(), airport_data, "Api response doesn't match airport data"
        )

    def test_search_airports(self):
        airport1 = Airport(
            code="ABC",
            name="",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=0,
            longitude=0,
        )
        airport2 = Airport(
            code="DEF",
            name="Some Airport",
            timezone="America/New_York",
            city="Richmond",
            state="Virginia",
            latitude=0,
            longitude=0,
        )
        db.session.add(airport1)
        db.session.add(airport2)
        db.session.commit()

        # Search for something that should return no results
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports", search="zxq"))
        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=0, expected_total_items=0)
        
        # Search for the first airport
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports", search="abc"))
        self.assertPaginatedResponse(response, expected_total_items=1)
        airport_data = response.json["items"][0]
        self.assertDictEqual(airport1.to_dict(), airport_data, "Api response doesn't match airport data")

        # Search for the second airport
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports", search="Some airport"))
        self.assertPaginatedResponse(response, expected_total_items=1)
        airport_data = response.json["items"][0]
        self.assertDictEqual(airport2.to_dict(), airport_data, "Api response doesn't match airport data")

        # Search for something they have in common
        with self.app.test_client() as client:
            response = client.get(url_for("api.airports", search="virginia"))
        self.assertPaginatedResponse(response, expected_total_items=2)

    def test_create_airport(self):
        airport_data = {
            "code": "AAA",
            "name": "test",
            "timezone": "America/New_York",
            "latitude": 100.5,
            "longitude": 29.65,
        }
        # Make sure anonymous users can't create an airport
        with self.app.test_client() as client:
            response = client.post(url_for("api.airports"), json=airport_data)
        self.assertApiResponse(response, 401)
        self.assertIn("message", response.json, "Api response missing message for 401 not authorized")

        # Login a non admin user and make sure they also can't create an airport
        with self.app.test_client(user=self.normal_user) as client:
            response = client.post(url_for("api.airports"), json=airport_data)
        self.assertApiResponse(response, 403)
        self.assertIn("message", response.json, "Api response missing message for 403 forbidden")

        # Login admin user and make sure they can create an airport
        with self.app.test_client(user=self.admin_user) as client:
            response = client.post(url_for("api.airports"), json=airport_data)
        self.assertApiResponse(response, 201)
        airport = Airport.query.first()
        self.assertIsNotNone(airport, "Airport not in database")
        self.assertDictEqual(airport.to_dict(), response.json, "Api response does not match airport data")

        # Make sure we get an error if we try to create an airport with the same code
        with self.app.test_client(user=self.admin_user) as client:
            response = client.post(url_for("api.airports"), json=airport_data)
        self.assertApiResponse(response, 409)
        self.assertIn("errors", response.json, "Api response missing errors")
        # Make sure the response has the "code" field in it
        self.assertIn("code", response.json["errors"], "Api response missing errors.code")

    def test_get_airport(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154,
        )
        db.session.add(airport)
        db.session.commit()

        # Test for valid aiport id
        with self.app.test_client() as client:
            response = client.get(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response)
        self.assertDictEqual(airport.to_dict(), response.json, "Api response does not match airport data")
        
        # Test for invalid airport id
        with self.app.test_client() as client:
            response = client.get(url_for("api.airport", id=airport.id + 1))
        self.assertApiResponse(response, 404)
        self.assertIn("message", response.json, "Api response missing message for 404 not found")

    def test_delete_airport(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154,
        )
        db.session.add(airport)
        db.session.commit()

        # Make sure anonymous users can't delete an airport
        with self.app.test_client() as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 401)
        self.assertIn("message", response.json, "Api response missing message for 401 not authorized")

        # Login a non admin user and make sure they also can't delete an airport
        with self.app.test_client(user=self.normal_user) as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 403)
        self.assertIn("message", response.json, "Api response missing message for 403 forbidden")

        # Login admin user and make sure they can delete an airport
        with self.app.test_client(user=self.admin_user) as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 204)
        self.assertIsNone(Airport.query.get(airport.id))
