import uuid

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


@api.resource("/customers")
class Customers(Resource):
    @role_required(["agent", "admin"])
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = models.Customer.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.User.to_collection_dict(
            query, page, items_per_page, "api.customers", search=search
        )
        return data

    @role_required(["agent", "admin"])
    def post(self):
        form = UserEditForm(data=request.json)
        if form.validate():
            user = models.Customer()
            form.populate_obj(user)
            # Set a random password.
            # The user will reset it later.
            user.set_password(uuid.uuid4().hex)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            # TODO: Send set password email
            return user.to_dict(), 201
        json_abort(400, message=form.errors)


@api.resource("/customers/<id>")
class Customer(Resource):
    @owner_or_role_required(["agent", "admin"])
    def get(self, id):
        user: models.Customer = get_or_404(models.Customer, id)
        return user.to_dict()


@api.resource("/agents")
class Agents(Resource):
    @role_required("admin")
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = models.Agent.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.User.to_collection_dict(
            query, page, items_per_page, "api.agents", search=search
        )
        return data

    @role_required("admin")
    def post(self):
        form = UserEditForm(formdata=request.json)
        if form.validate():
            user = models.Agent()
            form.populate_obj(user)
            # Set a random password.
            # The user will reset it later.
            user.set_password(uuid.uuid4().hex)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            # TODO: Send set password email
            return user.to_dict(), 201
        json_abort(400, message=form.errors)


@api.resource("/agents/<id>")
class Agent(Resource):
    @owner_or_role_required("admin")
    def get(self, id):
        user: models.Agent = get_or_404(models.Agent, id)
        return user.to_dict()


@api.resource("/admins")
class Admins(Resource):
    @role_required("admin")
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = models.Admin.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.User.to_collection_dict(
            query, page, items_per_page, "api.admins", search=search
        )
        return data

    @role_required("admin")
    def post(self):
        form = UserEditForm(formdata=request.json)
        if form.validate():
            user = models.Admin()
            form.populate_obj(user)
            # Set a random password.
            # The user will reset it later.
            user.set_password(uuid.uuid4().hex)
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            # TODO: Send set password email
            return user.to_dict(), 201
        json_abort(400, message=form.errors)


@api.resource("/admins/<id>")
class Admin(Resource):
    @role_required("admin")
    def get(self, id):
        user: models.Admin = get_or_404(models.Admin, id)
        return user.to_dict()


@api.resource("/users")
class Users(Resource):
    @role_required("admin")
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]

        query = models.User.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.User.to_collection_dict(
            query, page, items_per_page, "api.users", search=search
        )
        return data

@api.resource("/users/<id>")
class User(Resource):
    @role_required("admin")
    def get(self, id):
        user: models.User = get_or_404(models.User, id)
        return user.to_dict()