import logging

from flask import render_template
from flask_mail import Message

from app import mail


def send_email(subject, recipients, text_body, html_body):
    if not isinstance(recipients, list):
        recipients = [recipients]

    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    try:
        mail.send(msg)
    except Exception as e:
        logging.getLogger(__name__).error(
            "Unabled to send email", exc_info=e, stack_info=True
        )
        return False
    return True


def send_bulk_email(subject, recipients, text_template, html_template):
    with mail.connect() as conn:
        for email, data in recipients:
            msg = Message(subject=subject, recipients=[email])
            msg.body = render_template(text_template, **data)
            msg.html = render_template(html_template, **data)
            try:
                conn.send(msg)
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Unable to send email", exc_info=e, stack_info=True
                )
