from typing import Dict

from app.models import User

DEFAULT_PASSWORD = "abc123"


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MSEARCH_ENABLE = True
    MSEARCH_INDEX_NAME = "msearch_test"


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
