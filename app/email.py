import logging

from flask import render_template
from flask_mail import Message

from app import mail


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
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


def send_bulk_email(subject, sender, recipients, data, text_template, html_template):
    with mail.connect() as conn:
        for i, email in enumerate(recipients):
            msg = Message(subject=subject, sender=sender, recipients=[email])
            msg.body = render_template(text_template, **data[i])
            msg.html = render_template(html_template, **data[i])
            try:
                conn.send(msg)
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Unabled to send email", exc_info=e, stack_info=True
                )
