from distutils.util import strtobool
from flask_login import current_user
from sqlalchemy import func
from app import models, db
from app.api import api
from flask_restful import Resource, reqparse, request

from app.api.helpers import get_or_404, json_abort, owner_or_role_required
from app.forms import TransactionRefundForm


@api.resource("/purchases")
class Purchases(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("per_page", type=int, default=25, location="args")
        parser.add_argument("page", type=int, default=1, location="args")
        parser.add_argument("search", location="args")
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        items_per_page = args["per_page"]
        page = args["page"]
        search = args["search"]
        expand = args["expand"]

        query = models.PurchaseTransaction.query
        if search:
            query = query.msearch(f"{search}*")

        data = models.PurchaseTransaction.to_collection_dict(
            query, page, items_per_page, "api.userpurchases", id=id, expand=expand
        )
        return data


@api.resource("/purchases/<id>")
class Purchase(Resource):
    def get(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("expand", type=strtobool, default=False, location="args")

        args = parser.parse_args()
        expand = args["expand"]

        purchase = get_or_404(models.PurchaseTransaction, id)
        return purchase.to_dict(expand)


@api.resource("/users/<id>/purchases")
class UserPurchases(Resource):
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
            query, page, items_per_page, "api.userpurchases", id=id, expand=expand
        )
        return data


def _test_owner(**kwargs):
    id = kwargs.get("id")
    purchase: models.PurchaseTransaction = get_or_404(models.PurchaseTransaction, id)
    return purchase.email == current_user.email


@api.resource("/purchases/<id>/refund")
class PurchaseRefund(Resource):
    @owner_or_role_required(['agent', 'admin'], _test_owner)
    def post(self, id):
        purchase: models.PurchaseTransaction = get_or_404(models.PurchaseTransaction, id)
        form = TransactionRefundForm(data=request.json)
        if form.validate():
            for ticket_field in form.tickets:
                found = False
                for ticket in purchase.tickets:
                    if ticket.id == ticket_field.data:
                        found = True
                        ticket.refund_timestamp = func.now()
                        # TODO: What happens if the agent is refunding their own ticket?
                        # Should that be logged as "refunded by"?
                        if current_user.role == 'agent':
                            ticket.refunded_by = current_user.id
                if not found:
                    db.session.rollback()
                    json_abort(400, message=f"Ticket {ticket_field.data} does not belong to transaction {purchase.id}")
            db.session.commit()
            return "", 204