from app import db, models
from app.api import api
from app.api.helpers import json_abort
from app.forms import LoginForm, RegistrationForm
from flask_login import login_user, logout_user
from flask_restful import Resource, request


@api.resource("/login")
class Login(Resource):
    def post(self):
        form = LoginForm(data=request.json)
        if form.validate():
            user: models.User = form.email.data
            if not user.check_password(form.password.data):
                json_abort(400, message="Invalid username or password")

            login_user(user, remember=form.remember_me.data)
            return "", 204
        else:
            json_abort(400, message=form.errors)


@api.resource("/logout")
class Logout(Resource):
    def post(self):
        logout_user()
        return "", 204


@api.resource("/register")
class Register(Resource):
    def post(self):
        form = RegistrationForm(data=request.json)
        if form.validate():
            user = models.Customer(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            return user.to_dict(), 201
        json_abort(400, message=form.errors)
