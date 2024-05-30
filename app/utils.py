import random
import string
from app.models import (
    CropsStatus,
    FieldZone,
    Meta,
    MyModel,
    Notifications,
    Options,
    Role,
    Schedules,
    SoilStatus,
    Statistics,
    History,
    User,
    build_sample_db,
    db,
)
from flask import current_app
from flask_mailman import Mail, EmailMessage
generated_strings = set()


def generate_unique_string(length=10):
    while True:
        random_string = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=length))
        if random_string not in generated_strings:
            generated_strings.add(random_string)
            return random_string


def add_or_update_option(name, value):
    with current_app.app_context():
        option = Options.query.get(name)
        if not option:
            option = Options(option_name=name, option_value=value)
            db.session.add(option)
        else:
            option.option_value = value
        db.session.add(option)
        db.session.commit()
        return option.to_dict()

def send_invitation_email():
    pass
def send_notification_mail(subject: str, notification_body: str, emails: list):
    try:
        msg = EmailMessage(
            subject=subject,
            body=notification_body,
            to=emails,
            reply_to=['admin@tekon.co.zw']
        )
        msg.send()
        return True  # Return True if the email is sent successfully
    except Exception as e:
        print(f'An exception occurred: {e}')
        return False  # Return False if an exception occurs during the email sending process

    
