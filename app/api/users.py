import uuid

from sqlalchemy import update

from app import db, models
from app.api import api
from app.api.helpers import (
    get_or_404,
    json_abort,
    owner_or_role_required,
    role_required,
)
from app.forms import UserEditForm
from flask_restful import Resource, reqparse, request


class UsersResource(Resource):
    __model__ = models.User
    __endpoint__ = "api.users"

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = self.__model__.query
        if search:
            query = query.msearch(f"{search}*")

        data = self.__model__.to_collection_dict(
            query, page, items_per_page, self.__endpoint__, search=search
        )
        return data

    def post(self):
        form = UserEditForm(data=request.json)
        if form.validate():
            user = self.__model__()
            form.populate_obj(user)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            return user.to_dict(), 201
        json_abort(400, message=form.errors)


class UserResource(Resource):
    __model__ = models.User

    def get(self, id):
        user: self.__model__ = get_or_404(self.__model__, id)
        return user.to_dict()

    def delete(self, id):
        user: self.__model__ = get_or_404(self.__model__, id)
        db.session.delete(user)
        db.session.commit()
        return "", 204

    def patch(self, id):
        user = self.__model__ = get_or_404(self.__model__, id)
        form = UserEditForm(data=request.json)

        email_changed = False
        # Fix duplicate email error message
        if form.email.data == user.email:
            del form.email
        else:
            email_changed = True

        if form.validate():
            if email_changed:
                update(models.PurchaseTransaction).where(
                    models.PurchaseTransaction.email == user.email
                ).values(email=form.email.data)

            form.populate_obj(user)
            db.session.commit()
            db.session.refresh(user)
            return user.to_dict(), 200
        json_abort(400, message=form.errors)


@api.resource("/customers")
class Customers(UsersResource):
    __model__ = models.Customer
    __endpoint__ = "api.customers"

    @role_required(["agent", "admin"])
    def get(self):
        return super().get()

    @role_required(["agent", "admin"])
    def post(self):
        return super().post()


@api.resource("/customers/<id>")
class Customer(UserResource):
    __model__ = models.Customer

    @owner_or_role_required(["agent", "admin"])
    def get(self, id):
        return super().get(id)

    @owner_or_role_required(["agent", "admin"])
    def delete(self, id):
        return super().delete(id)

    @owner_or_role_required(["agent", "admin"])
    def patch(self, id):
        return super().patch(id)


@api.resource("/agents")
class Agents(UsersResource):
    __model__ = models.Agent
    __endpoint__ = "api.agents"

    @role_required("admin")
    def get(self):
        return super().get()

    @role_required("admin")
    def post(self):
        return super().post()


@api.resource("/agents/<id>")
class Agent(UserResource):
    __model__ = models.Agent

    @owner_or_role_required("admin")
    def get(self, id):
        return super().get(id)

    @owner_or_role_required("admin")
    def delete(self, id):
        return super().delete(id)

    @owner_or_role_required("admin")
    def patch(self, id):
        return super().patch(id)


@api.resource("/admins")
class Admins(UsersResource):
    __model__ = models.Admin
    __endpoint__ = "api.admins"

    @role_required("admin")
    def get(self):
        return super().get()

    @role_required("admin")
    def post(self):
        return super().post()


@api.resource("/admins/<id>")
class Admin(UserResource):
    __model__ = models.Admin

    @role_required("admin")
    def get(self, id):
        return super().get(id)

    @owner_or_role_required("admin")
    def delete(self, id):
        return super().delete(id)

    @owner_or_role_required("admin")
    def patch(self, id):
        return super().patch(id)


@api.resource("/users")
class Users(UsersResource):
    @role_required("admin")
    def get(self):
        return super().get()


@api.resource("/users/<id>")
class User(UserResource):
    @owner_or_role_required("admin")
    def get(self, id):
        return super().get(id)
