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
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required
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

def get_user_datastore()->SQLAlchemyUserDatastore:
    return current_app.config['USER_DATA_STORE']

def get_admin_user():
    with current_app.app_context():
        admin_user_email=get_option("company_admin_user")
        if admin_user_email:
            user_dstore=get_user_datastore()
            user=user_dstore.find_user(case_insensitive=True,email=admin_user_email)
            return user
        return None

def get_option(name:str):
    with current_app.app_context():
        option = db.session.get(Options, name)
        if not option:
            return None
        return option.option_value
def add_or_update_option(name, value):
    with current_app.app_context():
        option = db.session.get(Options, name)
        if not option:
            option = Options(option_name=name, option_value=value)
            db.session.add(option)
        else:
            option.option_value = value
        db.session.add(option)
        db.session.commit()
        return option.to_dict()


def send_notification_mail(subject: str, notification_body: str, emails: list):
    if not isinstance(emails, list):
        emails=[emails]
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

def get_super_and_admin_users_emails():
    return {user.email for user in get_super_and_admin_users()}


def get_super_and_admin_users()-> set:
    with current_app.app_context():
        admin_roles = Role.query.filter_by(name="super").filter_by(name="admin")
        users = set()  # Define users as a set
        for admin_role in admin_roles:
            users.update(admin_role.users)  # Add unique users to the set
        return users
    
def send_irrigation_stop_start_email(what,status,emails=None):
    current_time=datetime.datetime.now()
    if not emails:
        emails=get_super_and_admin_users_emails()
    return send_notification_mail(f"{what} Updates!",f"This is to notify you that {what} has {"started" if status else "Stopped"} at {current_time}",emails)
    

    
