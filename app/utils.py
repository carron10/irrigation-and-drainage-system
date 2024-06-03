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
    build_sample_db, Recommendation,
    db,
)
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required
)
from dateutil.rrule import MO
from dateutil.relativedelta import relativedelta
import pickle
import datetime
from flask import current_app
from flask_mailman import Mail, EmailMessage
import pandas as pd
import numpy as np
generated_strings = set()


def generate_unique_string(length=10):
    while True:
        random_string = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=length))
        if random_string not in generated_strings:
            generated_strings.add(random_string)
            return random_string


def get_user_datastore() -> SQLAlchemyUserDatastore:
    return current_app.config['USER_DATA_STORE']


def get_admin_user():
    with current_app.app_context():
        admin_user_email = get_option("company_admin_user")
        if admin_user_email:
            user_dstore = get_user_datastore()
            user = user_dstore.find_user(
                case_insensitive=True, email=admin_user_email)
            return user
        return None


def get_option(name: str):
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
    print("Email serveice was called", emails)
    if not isinstance(emails, list):
        emails = [emails]
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
    """
    Retrieve emails of users who have either the 'admin' or 'super' role.

    Returns:
        list: A list of emails of users who have the 'admin' or 'super' role.
    """
    return [user.email for user in get_super_and_admin_users()]


def get_super_and_admin_users() -> set:
    """
    Retrieve users who have either the 'admin' or 'super' role.

    Returns:
        set: A set of users who have the 'admin' or 'super' role.
    """
    with current_app.app_context():
        try:
            admin_roles = Role.query.filter(
                Role.name.in_(["admin", "super"])).all()
            users = set()  # Define users as a set
            for admin_role in admin_roles:
                users.update(admin_role.users)  # Add unique users to the set
            return users
        except Exception as e:
            # Handle exceptions (e.g., database query errors)
            # Log the error or raise a more specific exception as needed
            print(f"An error occurred: {e}")
            return set()  # Return an empty set in case of error


def send_irrigation_stop_start_email(what, status, emails=None):
    current_time = datetime.datetime.now()
    if emails == None:
        emails = get_super_and_admin_users_emails()
    action = "started" if status else "Stopped"
    return send_notification_mail(f"{what} Updates!", f"This is to notify you that {what} has {action} at {current_time}", emails)


ml_model = None
with open("KNN_MODLE.pkl", 'rb') as fl:
    ml_model = pickle.load(fl)

with open("Crop_categories.pkl", 'rb') as fl:
    crop_categories = pickle.load(fl)

with open("SOIL_categories.pkl", 'rb') as fl:
    soil_categories = pickle.load(fl)


def get_crop_cat_code(CROP):
    crop_code = crop_categories.cat.codes[crop_categories == CROP].iloc[0]
    return crop_code


def get_soil_cat_code(soil):
    soil_code = soil_categories.cat.codes[soil_categories == soil]
    if len(soil_code)>0:
        return soil_code.iloc[0]
    return None


def get_crop_name(code):
    crop = crop_categories.cat.categories[code]
    return crop


def ml_model_predict(data:pd.DataFrame):
    res=ml_model.predict(np.array(data))
    return res


def create_update_recommendations():
    with current_app.app_context():
        # Fetch SoilStatus objects from the database
        soils = SoilStatus.query.all()
        for soil in soils:
            # Get field from SoilStatus
            field = soil.field

            # Calculate start date three months back from today
            today = datetime.date.today()
            start_date = today - relativedelta(months=3)

            # Retrieve temperature data for the last three months
            temp_results = Statistics.query.filter_by(for_="Temperature") \
                                           .filter(Statistics.time_created >= start_date) \
                                           .filter(Statistics.time_created <= today) \
                                           .all()
            temp_values = [int(r.value) for r in temp_results]
            # print(temp_values)C
            
            avg_temp = np.mean(temp_values)

            # Retrieve humidity data for the last three months
            humidity_results = Statistics.query.filter_by(for_="Humidity") \
                                               .filter(Statistics.time_created >= start_date) \
                                               .filter(Statistics.time_created <= today) \
                                               .all()
            humidity_values = [int(r.value) for r in humidity_results]
        
            avg_humidity = np.mean(humidity_values)
            soil_code=get_soil_cat_code(soil)
            if not soil_code:
                continue
            # Prepare data for prediction
            data_to_predict = pd.DataFrame(
                {"SOIL_TYPE": [soil_code], "TEMPERATURE": avg_temp, "HUMIDITY": avg_humidity})

            # Predict recommended crop using ML model
            recommended_crop = ml_model_predict(data_to_predict)
            recommended_crop=recommended_crop[0]
            # Store recommendation in the database
            recommendation = Recommendation(tag=f"{field}_crop_recommendation",
                                            msg=f'It is recommended to plant {recommended_crop} in field zone {field}')
            db.session.add(recommendation)

        # Commit changes to the database session
        db.session.commit()


def get_recommendations():
    with current_app.app_context():
        create_update_recommendations()
        recommendations = Recommendation.query.all()
        return recommendations


def add_notification(msg):
    with current_app.app_context():
        note = Notifications(msg)
        db.session.add(note)
        db.session.commit()
