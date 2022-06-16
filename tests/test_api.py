import unittest

from flask import url_for

from app import create_app, db
from app.models import Airport, User

class TestConfig:
    SECRET_KEY = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MSEARCH_ENABLE = True
    MSEARCH_INDEX_NAME = 'msearch_test'

class TestAirports(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        self.client = self.app.test_client()
        db.create_all()
        self.admin_user = User(
            first_name='admin',
            last_name='user',
            email='adminuser@redeye.app',
            role='admin'
        )
        self.admin_user.set_password('abc123')
        db.session.add(self.admin_user)
        self.normal_user = User(
            first_name='test',
            last_name='user',
            email='testuser@redeye.app'
        )
        self.normal_user.set_password('abc123')
        db.session.add(self.normal_user)
        db.session.commit()
        db.session.refresh(self.admin_user)
        db.session.refresh(self.normal_user)

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_user(self, user: User) -> None:
        self.client.post('/login', data={
            'email': user.email, 
            'password': 'abc123'
        })

    def _logout_user(self) -> None:
        self.client.get('/logout')

    def test_get_airports(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154
        )
        db.session.add(airport)
        db.session.commit()
        response = self.client.get(url_for('api.airports'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertIn('_meta', response.json)
        self.assertEqual(response.json['_meta']['total_items'], 1)
        self.assertIn('_links', response.json)

        self.assertIn('items', response.json)
        airport_data = response.json['items'][0]
        self.assertDictEqual(airport_data, airport.to_dict())

    def test_search_airports(self):
        airport1 = Airport(
            code="ABC",
            name="",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=0,
            longitude=0
        )
        airport2 = Airport(
            code="DEF",
            name="Some Airport",
            timezone="America/New_York",
            city="Richmond",
            state="Virginia",
            latitude=0,
            longitude=0
        )
        db.session.add(airport1)
        db.session.add(airport2)
        db.session.commit()
        
        # Search for something that should return no results
        response = self.client.get(url_for('api.airports', search='zxq'))
        self.assertEqual(response.json['_meta']['total_items'], 0)
        # Search for the first airport
        response = self.client.get(url_for('api.airports', search='abc'))
        self.assertEqual(response.json['_meta']['total_items'], 1)
        airport_data = response.json['items'][0]
        self.assertDictEqual(airport_data, airport1.to_dict())
        # Search for the second airport
        response = self.client.get(url_for('api.airports', search='Some airport'))
        self.assertEqual(response.json['_meta']['total_items'], 1)
        airport_data = response.json['items'][0]
        self.assertDictEqual(airport_data, airport2.to_dict())
        # Search for something they have in common
        response = self.client.get(url_for('api.airports', search='virginia'))
        self.assertEqual(response.json['_meta']['total_items'], 2)

    def test_create_airport(self):
        airport_data = {
            "code": "AAA",
            "name": "test",
            "timezone": "America/New_York",
            "latitude": 100.5,
            "longitude": 29.65
        }
        # Make sure anonymous users can't create an airport
        response = self.client.post(url_for('api.airports'), json=airport_data)
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.is_json)
        self.assertDictEqual(response.json, {'message': 'Not authorized'})
        # Login a non admin user and make sure they also can't create an airport
        self._login_user(self.normal_user)
        response = self.client.post(url_for('api.airports'), json=airport_data)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.is_json)
        self.assertDictEqual(response.json, {'message': 'Forbidden'})
        # Login admin user and make sure they can create an airport
        self._logout_user()
        self._login_user(self.admin_user)
        response = self.client.post(url_for('api.airports'), json=airport_data)
        self.assertEqual(response.status_code, 201)
        airport = Airport.query.first()
        self.assertIsNotNone(airport)
        self.assertDictEqual(response.json, airport.to_dict())
        # Make sure we get an error if we try to create an airport with the same code
        response = self.client.post(url_for('api.airports'), json=airport_data)
        self.assertEqual(response.status_code, 409)
        self.assertIn('errors', response.json)
        # Make sure the response has the "code" field in it
        self.assertIn('code', response.json['errors'])

    def test_get_airport(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154
        )
        db.session.add(airport)
        db.session.commit()
        response = self.client.get(url_for('api.airport', id=airport.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertDictEqual(response.json, airport.to_dict())

    def test_delete_airport(self):
        airport = Airport(
            code="ORF",
            name="Norfolk International Airport",
            timezone="America/New_York",
            city="Norfolk",
            state="Virginia",
            latitude=36.8977,
            longitude=-76.2154
        )
        db.session.add(airport)
        db.session.commit()
        # Make sure anonymous users can't delete an airport
        response = self.client.delete(url_for('api.airport', id=airport.id))
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.is_json)
        self.assertDictEqual(response.json, {'message': 'Not authorized'})
        # Login a non admin user and make sure they also can't delete an airport
        self._login_user(self.normal_user)
        response = self.client.delete(url_for('api.airport', id=airport.id))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.is_json)
        self.assertDictEqual(response.json, {'message': 'Forbidden'})
        # Login admin user and make sure they can delete an airport
        self._logout_user()
        self._login_user(self.admin_user)
        response = self.client.delete(url_for('api.airport', id=airport.id))
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(Airport.query.get(airport.id))
