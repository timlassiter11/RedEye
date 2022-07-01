from flask import url_for
from flask_login import login_user
from werkzeug.test import TestResponse
from werkzeug.exceptions import HTTPException

from app import db
from app.api.helpers import code_to_airport, get_or_404, json_abort, login_required, role_required
from app.models import Airplane, Airport, User
from helpers import create_users, create_airports, add_to_db, FlaskTestCase


class ApiTestCase(FlaskTestCase):
    def setUp(self) -> None:
        super().setUp()
        users = create_users()
        self.admin_user = users["admin"]
        self.agent_user = users["agent"]
        self.customer_user = users["customer"]

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


class TestHelpers(ApiTestCase):
    def test_json_abort(self):
        data = {"message": "test"}
        with self.assertRaises(HTTPException) as cm:
            json_abort(400, **data)

        ex = cm.exception
        self.assertApiResponse(ex.response, 400)
        self.assertDictEqual(data, ex.response.json)

    def test_login_required(self):
        f = login_required(lambda: True)
        with self.app.test_client():
            with self.assertRaises(HTTPException) as cm:
                f()

            ex = cm.exception
            self.assertApiResponse(ex.response, 401)
            self.assertIn("message", ex.response.json)

        # Login each user type and make sure we don't get an exception
        with self.app.test_request_context():
            login_user(self.customer_user)
            self.customer_user.authenticated = True
            self.assertTrue(f())

        with self.app.test_request_context():
            login_user(self.agent_user)
            self.agent_user.authenticated = True
            self.assertTrue(f())

        with self.app.test_request_context():
            login_user(self.admin_user)
            self.admin_user.authenticated = True
            self.assertTrue(f())

    def test_single_role_required(self):
        f = role_required('admin')(lambda: True)
        # Make sure we get a 401 with no user
        with self.app.test_client():
            with self.assertRaises(HTTPException) as cm:
                f()

            ex = cm.exception
            self.assertApiResponse(ex.response, 401)
            self.assertIn("message", ex.response.json)

        # Make sure we got a 403 with both customer and agent
        with self.app.test_request_context():
            login_user(self.customer_user)
            self.customer_user.authenticated = True
            with self.assertRaises(HTTPException) as cm:
                f()
            ex = cm.exception
            self.assertApiResponse(ex.response, 403)

        with self.app.test_request_context():
            login_user(self.agent_user)
            self.agent_user.authenticated = True
            with self.assertRaises(HTTPException) as cm:
                f()
            ex = cm.exception
            self.assertApiResponse(ex.response, 403)

        # Make sure we don't get an exception with admin
        with self.app.test_request_context():
            login_user(self.admin_user)
            self.admin_user.authenticated = True
            self.assertTrue(f())

    def test_multiple_role_required(self):
        f = role_required(['admin', 'customer'])(lambda: True)
        # Make sure we get a 401 with no user
        with self.app.test_client():
            with self.assertRaises(HTTPException) as cm:
                f()

            ex = cm.exception
            self.assertApiResponse(ex.response, 401)
            self.assertIn("message", ex.response.json)

        # Make sure we got a 403 with agent
        with self.app.test_request_context():
            login_user(self.agent_user)
            self.agent_user.authenticated = True
            with self.assertRaises(HTTPException) as cm:
                f()
            ex = cm.exception
            self.assertApiResponse(ex.response, 403)

        # Make sure we don't get any excpetions with both admin and customer
        with self.app.test_request_context():
            login_user(self.customer_user)
            self.customer_user.authenticated = True
            self.assertTrue(f())

        with self.app.test_request_context():
            login_user(self.admin_user)
            self.admin_user.authenticated = True
            self.assertTrue(f())

    def test_get_or_404(self):
        with self.assertRaises(HTTPException) as cm:
            get_or_404(User, 5)

        ex = cm.exception
        self.assertApiResponse(ex.response, 404)
        self.assertIn("message", ex.response.json)

        u = get_or_404(User, self.admin_user.id)
        self.assertEquals(self.admin_user.email, u.email)

    def test_code_to_airport(self):
        with self.assertRaises(ValueError):
            code_to_airport("ABC")

        airports = create_airports(count=1)
        airport1 = list(airports.values())[0]
        airport2 = code_to_airport(airport1.code)

        self.assertEquals(airport1.id, airport2.id)

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

        add_to_db(airport)
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
        
        add_to_db([airport1, airport2])

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
        with self.app.test_client(user=self.customer_user) as client:
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
        self.assertIn("message", response.json, "Api response missing message")
        # Make sure the response has the "code" field in it
        self.assertIn("code", response.json["message"], "Api response missing message.code")

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

        add_to_db(airport)

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
        
        add_to_db(airport)

        # Make sure anonymous users can't delete an airport
        with self.app.test_client() as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 401)
        self.assertIn("message", response.json, "Api response missing message for 401 not authorized")

        # Login a non admin user and make sure they also can't delete an airport
        with self.app.test_client(user=self.customer_user) as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 403)
        self.assertIn("message", response.json, "Api response missing message for 403 forbidden")

        # Login admin user and make sure they can delete an airport
        with self.app.test_client(user=self.admin_user) as client:
            response = client.delete(url_for("api.airport", id=airport.id))
        self.assertApiResponse(response, 204)
        self.assertIsNone(Airport.query.get(airport.id))

class TestAirplanes(ApiTestCase):       
    def test_get_airplanes(self):
        airplane = Airplane(
            registration_number="N1234RE",
            model_name="Boeing 737",
            model_code="B737-800",
            capacity=189,
            range=1995,
        )
        
        # Test to make sure everything works with no airplanes
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes"))
        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=0, expected_total_items=0)

        add_to_db(airplane)

        # Test to make sure everything works with a single airplane
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes"))

        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=1, expected_total_items=1)
        airplane_data = response.json["items"][0]
        self.assertDictEqual(
            airplane.to_dict(), airplane_data, "Api response doesn't match airplane data"
        )

    def test_search_airplanes(self):
        airplane1 = Airplane(
            registration_number="N123RE",
            model_name="Boeing 737",
            model_code="B737-800",
            capacity=189,
            range=3300,
        )
        airplane2 = Airplane(
            registration_number="N456RE",
            model_name="Airbus A320",
            model_code="A320",
            capacity=150,
            range=3300,
        )
        
        add_to_db([airplane1, airplane2])
        

        # Search for something that should return no results
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes", search="N789RE"))
        self.assertPaginatedResponse(response, expected_page=1, expected_total_pages=0, expected_total_items=0)
        
        # Search for the first airplane
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes", search=airplane1.registration_number))
        self.assertPaginatedResponse(response, expected_total_items=1)
        airplane_data = response.json["items"][0]
        self.assertDictEqual(airplane1.to_dict(), airplane_data, "Api response doesn't match airplane data")

        # Search for the second airplane
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes", search="air"))
        self.assertPaginatedResponse(response, expected_total_items=1)
        airplane_data = response.json["items"][0]
        self.assertDictEqual(airplane2.to_dict(), airplane_data, "Api response doesn't match airplane data")

        # Search for something they have in common
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplanes", search="N"))
        self.assertPaginatedResponse(response, expected_total_items=2)

    def test_create_airplane(self):
        airplane_data = {
            "registration_number": "N456RE",
            "model_name": "Airbus A320",
            "model_code": "A320",
            "capacity": 150,
            "range": 3300,
        }
        # Make sure anonymous users can't create an airplane
        with self.app.test_client() as client:
            response = client.post(url_for("api.airplanes"), json=airplane_data)
        self.assertApiResponse(response, 401)
        self.assertIn("message", response.json, "Api response missing message for 401 not authorized")

        # Login a non admin user and make sure they also can't create an airplane
        with self.app.test_client(user=self.customer_user) as client:
            response = client.post(url_for("api.airplanes"), json=airplane_data)
        self.assertApiResponse(response, 403)
        self.assertIn("message", response.json, "Api response missing message for 403 forbidden")

        # Login admin user and make sure they can create an airplane
        with self.app.test_client(user=self.admin_user) as client:
            response = client.post(url_for("api.airplanes"), json=airplane_data)
        self.assertApiResponse(response, 201)
        airplane = Airplane.query.first()
        self.assertIsNotNone(airplane, "Airplane not in database")
        self.assertDictEqual(airplane.to_dict(), response.json, "Api response does not match airplane data")

        # Make sure we get an error if we try to create an airplane with the same registration_number
        with self.app.test_client(user=self.admin_user) as client:
            response = client.post(url_for("api.airplanes"), json=airplane_data)
        self.assertApiResponse(response, 409)
        self.assertIn("message", response.json, "Api response missing message")
        # Make sure the response has the "code" field in it
        self.assertIn("registration_number", response.json["message"], "Api response missing message.registration_number")

    def test_get_airplane(self):
        airplane = Airplane(
            registration_number="N123RE",
            model_name="Boeing 737",
            model_code="B737-800",
            capacity=189,
            range=3300,
        )

        add_to_db(airplane)

        # Test for valid airplane id
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplane", id=airplane.id))
        self.assertApiResponse(response)
        self.assertDictEqual(airplane.to_dict(), response.json, "Api response does not match airplane data")
        
        # Test for invalid airplane id
        with self.app.test_client() as client:
            response = client.get(url_for("api.airplane", id=airplane.id + 1))
        self.assertApiResponse(response, 404)
        self.assertIn("message", response.json, "Api response missing message for 404 not found")

    def test_delete_airplane(self):
        airplane = Airplane(
            registration_number="N123RE",
            model_name="Boeing 737",
            model_code="B737-800",
            capacity=189,
            range=3300,
        )
        
        add_to_db(airplane)

        # Make sure anonymous users can't delete an airplane
        with self.app.test_client() as client:
            response = client.delete(url_for("api.airplane", id=airplane.id))
        self.assertApiResponse(response, 401)
        self.assertIn("message", response.json, "Api response missing message for 401 not authorized")

        # Login a non admin user and make sure they also can't delete an airplane
        with self.app.test_client(user=self.customer_user) as client:
            response = client.delete(url_for("api.airplane", id=airplane.id))
        self.assertApiResponse(response, 403)
        self.assertIn("message", response.json, "Api response missing message for 403 forbidden")

        # Login admin user and make sure they can delete an airplane
        with self.app.test_client(user=self.admin_user) as client:
            response = client.delete(url_for("api.airplane", id=airplane.id))
        self.assertApiResponse(response, 204)
        self.assertIsNone(Airplane.query.get(airplane.id))
