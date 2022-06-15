import logging
from threading import Thread

from flask import current_app
from flask_mail import Message

from app import mail


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            logging.getLogger(__name__).error('Unabled to send email', exc_info=e, stack_info=True)


def send_email(subject, sender, recipients, text_body, html_body,
               attachments=None, sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        try:
            mail.send(msg)
        except Exception as e:
            logging.getLogger(__name__).error('Unabled to send email', exc_info=e, stack_info=True)
            return False
    else:
        Thread(target=send_async_email,
            args=(current_app._get_current_object(), msg)).start()
    return True
