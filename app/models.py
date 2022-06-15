import datetime
import time
from typing import Any, Dict

import jwt
from flask import current_app, url_for
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login


class PaginatedAPIMixin:
    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = dict(self.__dict__)
        # SQLAlchemy models contain an extra field that we don't want to expose.
        data.pop("_sa_instance_state", None)
        for key, value in data.items():
            if isinstance(value, datetime.time):
                data[key] = str(value)

        if "id" in data:
            data["self"] = url_for(self.__endpoint__, id=data["id"])
            del data["id"]

        return data

    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, expand=False, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            "items": [item.to_dict(expand=expand) for item in resources.items],
            "_meta": {
                "page": page,
                "per_page": per_page,
                "total_pages": resources.pages,
                "total_items": resources.total,
            },
            "_links": {
                "self": url_for(endpoint, page=page, per_page=per_page, **kwargs),
                "next": url_for(endpoint, page=page + 1, per_page=per_page, **kwargs)
                if resources.has_next
                else None,
                "prev": url_for(endpoint, page=page - 1, per_page=per_page, **kwargs)
                if resources.has_prev
                else None,
            },
        }
        return data


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(10), default="user")

    def __repr__(self):
        return f"<User {self.first_name} {self.last_name}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time.time() + expires_in},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["reset_password"]
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Airport(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.airport"
    __searchable__ = ["code", "name", "city", "state"]

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), index=True, unique=True)
    name = db.Column(db.String(120), nullable=False)
    timezone = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    latitude = db.Column(db.Integer, nullable=False)
    longitude = db.Column(db.Integer, nullable=False)
    airplanes = db.relationship("Airplane", backref="home")


class Airplane(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.airplane"
    __searchable__ = ["registration_number", "model_name", "model_code"]

    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(120), index=True, unique=True)
    model_name = db.Column(db.String(120), nullable=False)
    model_code = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    range = db.Column(db.Integer, nullable=False)
    home_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    flights = db.relationship("Flight", backref="airplane")

    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = super().to_dict()
        if expand:
            data["home"] = self.home.to_dict()
        else:
            data["home"] = url_for(self.home.__endpoint__, id=self.home.id)
        return data


class Flight(PaginatedAPIMixin, db.Model):
    __endpoint__ = "api.flight"
    __searchable__ = ["number"]

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(4), index=True)
    airplane_id = db.Column(db.Integer, db.ForeignKey("airplane.id"))
    departure_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    arrival_id = db.Column(db.Integer, db.ForeignKey("airport.id"))
    departure_time = db.Column(db.Time, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    cost = db.Column(db.Float, nullable=False)

    departure_airport = db.relationship(
        "Airport", foreign_keys=[departure_id], backref="departures"
    )
    arrival_airport = db.relationship(
        "Airport", foreign_keys=[arrival_id], backref="arrivals"
    )

    def to_dict(self, expand=False) -> Dict[str, Any]:
        data = super().to_dict()
        if expand:
            data["airplane"] = self.airplane.to_dict()
            data["departure_airport"] = self.departure_airport.to_dict()
            data["arrival_airport"] = self.arrival_airport.to_dict()
        else:
            data["airplane"] = url_for(self.airplane.__endpoint__, id=self.airplane.id)
            data["departure_airport"] = url_for(
                self.departure_airport.__endpoint__, id=self.departure_id
            )
            data["arrival_airport"] = url_for(
                self.departure_airport.__endpoint__, id=self.arrival_id
            )

        return data


"""
class PurchasedFlight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight = db.Column(db.Integer, db.ForeignKey('flight.id'))
    purchased_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assisted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    departure_date = db.Column(db.Date, nullable=False)
"""
