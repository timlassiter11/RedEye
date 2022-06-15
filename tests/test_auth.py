import unittest

from app import create_app, db
from app.models import User

class TestConfig:
    SECRET_KEY = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    TESTING = True

class TestAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        self.user_data = {
            'first_name': 'test',
            'last_name': 'user',
            'email': 'testuser@redeye.app',
            'password': 'abc123',
            'password2': 'abc123'
        }

        with self.app.app_context():
            db.create_all()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


    def test_register(self):
        # Make sure the GET method works
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)

        # Make sure the POST method works and redirects to '/' on successful registration
        response = self.client.post("/register", data=self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')

        with self.app.app_context():
            user: User = User.query.filter_by(email=self.user_data['email']).first()
            
            self.assertIsNotNone(user)
            self.assertEqual(user.first_name, self.user_data['first_name'])
            self.assertEqual(user.last_name, self.user_data['last_name'])
            self.assertEqual(user.email, self.user_data['email'])
            self.assertTrue(user.check_password(self.user_data['password']))
            assert user.check_password(self.user_data['password'])

    def test_login(self):
        # Create a test user so we can verify login
        with self.app.app_context():
            user = User(
                email=self.user_data['email'],
                first_name=self.user_data['first_name'],
                last_name=self.user_data['last_name']
            )
            user.set_password(self.user_data['password'])
            db.session.add(user)
            db.session.commit()

        # Make sure the GET method works
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

        # Make sure the POST method works and redirects to '/' on successful login
        response = self.client.post('/login', data={
            'email': self.user_data['email'], 
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')
