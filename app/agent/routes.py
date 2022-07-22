from app.agent import bp
from app.forms import FlightCancellationForm
from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user


@bp.before_request
def restrict_bp_to_admins():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for(request.endpoint)))

    if current_user.role != "agent":
        abort(403)


@bp.route("/")
@bp.route("/sales")
def sales():
    return render_template("agent/sales.html")


@bp.route("/flights")
def flights():
    form = FlightCancellationForm()
    return render_template("agent/flights.html", form=form)


@bp.route("/transactions")
def transactions():
    return render_template("agent/transactions.html")
