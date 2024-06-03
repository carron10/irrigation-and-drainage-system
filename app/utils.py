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
    """To generate unique string 

    Args:
        length (int, optional): The length of string. Defaults to 10.

    Returns:
        str: unique string
    """
    while True:
        random_string = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=length))
        if random_string not in generated_strings:
            generated_strings.add(random_string)
            return random_string


def get_user_datastore() -> SQLAlchemyUserDatastore:
    """To get and return the user data store that have been stored in app config

    Returns:
        SQLAlchemyUserDatastore: user data store, for user management
    """
    return current_app.config['USER_DATA_STORE']


def get_admin_user()->User:
    """To get the user used when setuping up the app

    Returns:
        User: admin user
    """
    with current_app.app_context():
        admin_user_email = get_option("company_admin_user")
        if admin_user_email:
            user_dstore = get_user_datastore()
            user = user_dstore.find_user(
                case_insensitive=True, email=admin_user_email)
            return user
        return None


def get_option(name: str)-> str:
    """Get the option from the Options table

    Args:
        name (str):option to return

    Returns:
        str: option value or None if not found
    """
    with current_app.app_context():
        option = db.session.get(Options, name)
        if not option:
            return None
        return option.option_value


def add_or_update_option(name, value)-> dict:
    """Update an option in the database or create a new one if not exist

    Args:
        name (_type_): option name
        value (_type_): option value

    Returns:
        dict: Option after adding to db
    """
    with current_app.app_context():
        
        #check if alread exist
        option = db.session.get(Options, name)
        if not option:
            option = Options(option_name=name, option_value=value)
            db.session.add(option)
        else:
            option.option_value = value
        db.session.add(option)
        db.session.commit()
        return option.to_dict()


def send_notification_mail(subject: str, notification_body: str, emails: list)->bool:
    """To send email to given emails,

    Args:
        subject (str): Email subject
        notification_body (str):Email body
        emails (list): list of emails to send to
    Returns:
        bool: whether the email was sent or not
    """
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


def send_irrigation_stop_start_email(what:str, status:bool, emails:list=None)-> bool:
    """To send email to users when irrigation/drainage starts or stops

    Args:
        what (str): what was started irrigation/drainage
        status (bool): indicate whether [what] was stopped or started
        emails (list, optional): list of emails to send to. Defaults to None.

    Returns:
        bool: email was delivered or not
    """
    current_time = datetime.datetime.now()
    if emails == None:
        #get super and admin emails if emails not provideed
        emails = get_super_and_admin_users_emails()
    #is it started or stopped
    action = "started" if status else "Stopped"
    return send_notification_mail(f"{what} Updates!", f"This is to notify you that {what} has {action} at {current_time}", emails)


##########################################
#  FUNCTIONS TO HANDLE ML RECOMMENDATIONS#
##########################################


ml_model = None

#Load the model from file
with open("KNN_MODLE.pkl", 'rb') as fl:
    ml_model = pickle.load(fl)

#Load the crops from file
with open("Crop_categories.pkl", 'rb') as fl:
    crop_categories = pickle.load(fl)

#Load the Soil types
#The ML can only able to predict given any from these
with open("SOIL_categories.pkl", 'rb') as fl:
    soil_categories = pickle.load(fl)


def get_crop_cat_code(CROP)->int:
    """get crop category code from categories

    Args:
        CROP (_type_): Crop to get the code for

    Returns:
        int: crop code
    """
    crop_code = crop_categories.cat.codes[crop_categories == CROP].iloc[0]
    return crop_code


def get_soil_cat_code(soil)-> int:
    
    soil_code = soil_categories.cat.codes[soil_categories == soil]
    if len(soil_code)>0:
        return soil_code.iloc[0]
    return None


def get_crop_name(code):
    crop = crop_categories.cat.categories[code]
    return crop


def ml_model_predict(data:pd.DataFrame):
    """Predict given the data and return the prediction

    Args:
        data (pd.DataFrame): data containing the features...
    Returns:
        array:array of predicted values
    """
    res=ml_model.predict(np.array(data))
    return res


def create_update_recommendations():
    """create new recommendations or update the already existing one
    """
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
            soil_code=get_soil_cat_code(soil.soil_type)
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


def get_recommendations()->Recommendation:
    """Get recommendations from the database

    Returns:
        Recommendation: list of recormmendations
    """
    with current_app.app_context():
        #call the update first
        create_update_recommendations()
        recommendations = Recommendation.query.all()
        return recommendations


def add_notification(msg:str):
    """Add a notification to

    Args:
        msg (str): msg to store
    """
    with current_app.app_context():
        note = Notifications(msg)
        db.session.add(note)
        db.session.commit()
