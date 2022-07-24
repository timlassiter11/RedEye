import calendar
import datetime as dt

from app.agent import bp
from app.forms import FlightCancellationForm, TransactionRefundForm
from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user


@bp.before_request
def restrict_bp_to_admins():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for(request.endpoint)))

    if current_user.role != "agent":
        abort(403)


@bp.route("/")
def sales():
    start = dt.date.today().replace(day=1)
    _, days = calendar.monthrange(start.year, start.month)
    end = start.replace(day=days)
    agent_sales = current_user.sales_by_date(start, end)
    return render_template("agent/sales.html", sales=agent_sales)


@bp.route("/flights")
def flights():
    form = FlightCancellationForm()
    return render_template("agent/flights.html", form=form)


@bp.route("/transactions")
def transactions():
    form = TransactionRefundForm()
    return render_template("agent/transactions.html", form=form)
