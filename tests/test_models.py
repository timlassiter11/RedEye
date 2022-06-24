from app import db
from app.models import User
from helpers import FlaskTestCase

class TestUser(FlaskTestCase):
    def test_password(self):
        user = User()
        password = 'abc&^%123'
        user.set_password(password)
        self.assertFalse(user.check_password(password[::-1]))
        self.assertTrue(user.check_password(password))

    def test_reset_token(self):
        user = User(
            email='testuser@redeye.app',
            first_name='test',
            last_name='user'
        )
        user.set_password('abc123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = user.get_reset_password_token()
        jwt_user = User.verify_reset_password_token(token[::-1])
        self.assertIsNone(jwt_user)
        jwt_user = User.verify_reset_password_token(token)
        self.assertEquals(user.id, jwt_user.id)
    