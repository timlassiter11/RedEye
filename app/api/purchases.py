from distutils.util import strtobool

from app import db, models
from app.api import api
from app.api.helpers import get_or_404, json_abort, owner_or_role_required
from app.email import send_email
from app.forms import TransactionRefundForm
from flask import render_template
from flask_login import current_user
from flask_restful import Resource, reqparse, request
from sqlalchemy import func


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
    @owner_or_role_required(["admin", "agent"])
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
    @owner_or_role_required(["agent", "admin"], _test_owner)
    def post(self, id):
        purchase: models.PurchaseTransaction = get_or_404(
            models.PurchaseTransaction, id
        )
        form = TransactionRefundForm(data=request.json)
        if form.validate():
            fare_refund = 0
            refunded_tickets = []
            for ticket_field in form.tickets:
                found = False
                for ticket in purchase.tickets:
                    if ticket.id == ticket_field.data:
                        found = True
                        # Only refund tickets that haven't already been refunded.
                        if ticket.refund_timestamp is None:
                            refunded_tickets.append(ticket)
                            ticket.refund_timestamp = func.now()
                            fare_refund += ticket.purchase_price
                            # TODO: What happens if the agent is refunding their own ticket?
                            # Should that be logged as "refunded by"?
                            if current_user.role == "agent":
                                ticket.refunded_by = current_user.id

                if not found:
                    db.session.rollback()
                    json_abort(
                        400,
                        message=f"Ticket {ticket_field.data} does not belong to transaction {purchase.id}",
                    )
            db.session.commit()

            taxes_refund = (purchase.taxes / len(purchase.tickets)) * len(refunded_tickets)

            text_body = render_template(
                "email/return.txt",
                fare_refund=fare_refund,
                taxes_refund=taxes_refund,
                refunded_tickets=refunded_tickets,
            )
            html_body = render_template(
                "email/return.html",
                fare_refund=fare_refund,
                taxes_refund=taxes_refund,
                refunded_tickets=refunded_tickets,
            )
            send_email("Purchase Refund", [purchase.email], text_body, html_body)

            return "", 204
        
        json_abort(400, message=form.errors)
