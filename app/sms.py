from twilio.rest import Client
from flask import current_app


def send_test_alert():
    client = Client(
        current_app.config['TWILIO_ACCOUNT_SID'],
        current_app.config['TWILIO_AUTH_TOKEN']
    )
    message = client.messages.create(
        body="sms_internal_alerts",  # trial accounts must use a predefined template name here
        from_=current_app.config['TWILIO_FROM_NUMBER'],
        to=current_app.config['ALERT_TO_NUMBER']
    )
    return message.sid