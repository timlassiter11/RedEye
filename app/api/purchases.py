from distutils.util import strtobool
from flask_login import current_user
from app import models
from app.api import api
from flask_restful import Resource, reqparse

from app.api.helpers import get_or_404, owner_or_role_required

@api.resource("/users/<id>/purchases")
class Purchases(Resource):
    @owner_or_role_required(['admin', 'agent'])
    def get(self, id):
        user: models.User = get_or_404(models.User, id)
        
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        expand = args["expand"]

        query = models.PurchaseTransaction.query.filter_by(email=user.email)
        data = models.PurchaseTransaction.to_collection_dict(
            query, page, items_per_page, "api.purchases", id=id, expand=expand
        )
        return data


@api.resource("/purchases/<id>")
class Purchase(Resource):
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        expand = args["expand"]

        purchase: models.PurchaseTransaction = get_or_404(models.PurchaseTransaction, id)
        return purchase.to_dict(expand)