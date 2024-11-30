import datetime
from datetime import timedelta
import json
import os
import time
from schedule import Scheduler
import schedule
from threading import Event
import psycopg2
from sqlalchemy import func
from flask import (
    Blueprint,
    Flask,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required,
)
from flask_security.forms import RegisterForm, Required, StringField
from flask_security.utils import hash_password
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Table, select, update, desc, asc
from sqlalchemy.ext.declarative import declared_attr

from app import create_app
from app.micro_controllers_ws_server import (
    connected_devices,
    get_all_connected_sensors,
    websocket,
    start_stop_irrigation_and_drainage,
    send_command,
    send_data,
    get_sensor_value,
)
import pandas as pd
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
from app.websocket.flask_sock import Sock
from threading import Thread
from app.utils import (
    generate_unique_string, add_notification, send_irrigation_stop_start_email,
    send_notification_mail, get_admin_user, get_super_and_admin_users_emails, get_recommendations)
from app.user_routes import user_bp, security, user_datastore

from flask_mailman import Mail, EmailMessage


app = create_app()

app.register_blueprint(user_bp)

security.init_app(app)

app.user_datastore = user_datastore
app.security = security

app.config["SQLALCHEMY_MODEL_BASE_CLASS"] = MyModel
scheduler = Scheduler()
app.scheduler = scheduler
# app.config["SCHEDULER"] = scheduler
db.init_app(app)

# create mail object
mail = Mail(app)


# Before request check if the a setup have been done
@app.before_request
def before_request_handler():
    "Before a request check that the Website setup have been already or not!"
    if request.path == '/login':
        super_role = Role.query.filter_by(name="super").first()
        if super_role:
            admin_users_count = super_role.users.count()
            if admin_users_count == 0:
                return redirect(url_for('user_bp.setup'))
        else:
            return redirect(url_for('user_bp.setup'))


# Function to execute when one visit /api/notifications
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """To get notifications

    Returns:
        list: list of notifications with given limit,
    """
    limit = request.args.get("limit")
    if not limit:
        limit = 20
    results = db.session.execute(select(Notifications).limit(limit)).scalars()
    return [r.to_dict() for r in results]


# Returns users registered in this app
# Accep limit as int, which specifies the limit of users to return
@app.route("/api/users", methods=["GET"])
def get_users():
    """get users .
    --Make an http get request with limit:int param
    Returns:
        list: List of users with given limit
    """
    limit = request.args.get("limit")
    if not limit:
        limit = 20
    results = User.query.limit(limit).all()
    return [r.to_dict(rules=["-password", "-roles"]) for r in results]


# Getting historical data
@app.route("/api/history/<for_>", methods=["GET"])
def get_history(for_):
    """Return sensors reading history

    Returns:
        List of sensor readings history
    """
    echological = ['Temperature', 'Humidity', 'SoilMoisture']
    results = []
    interval = request.args.get('interval')

    # check if the interval is accepted or not
    if not (interval in ['daily', 'hourly', 'monthly', 'yearly', 'quarterly']):
        return "Interval should be one of daily,hourly,monthly or yearly"

    # metric should be sum or averge
    metric = request.args.get('metric')
    metric = 'sum' if not metric else metric
    if not (metric in ['sum', 'average']):
        return "Metric should be sum or average", 404

    start_date = datetime.datetime.strptime(
        request.args.get('start'), "%d-%m-%Y")
    end_date = datetime.datetime.strptime(request.args.get('end'), "%d-%m-%Y")
    # results = db.session.query(Statistics).filter(
    #     Statistics.for_ == for_).all()
    # return [r.to_dict() for r in results]
    time_col = 'end_time'
    if for_ in echological:
        results = db.session.query(Statistics).filter(
            Statistics.for_ == for_).filter(
            Statistics.time_created >= start_date).filter(
            Statistics.time_created <= end_date).all()
        time_col = "time_created"
    else:
        results = db.session.query(History).filter(
            History.for_ == for_).filter(
            History.end_time >= start_date).filter(
            History.end_time <= end_date).all()

    results = [r.to_dict() for r in results]
    df = pd.DataFrame(results, columns=[time_col, 'value'])
    df[time_col] = pd.to_datetime(df[time_col])
    df['value'] = pd.to_numeric(df['value'])

    interval_df = None
    df.set_index(time_col, inplace=True)
    if interval == 'daily':
        interval_df = df.resample('D').sum(
        ) if metric == 'sum' else df.resample('D').mean()
    elif interval == 'monthly':
        interval_df = df.resample('M').sum(
        ) if metric == 'sum' else df.resample('M').mean()
    elif interval == 'weekly':
        interval_df = df.resample('W').sum(
        ) if metric == 'sum' else df.resample('W').mean()
    elif interval == 'yearly':
        interval_df = df.resample('Y').sum(
        ) if metric == 'sum' else df.resample('Y').mean()
    elif interval == 'hourly':
        interval_df = df.resample('H').sum(
        ) if metric == 'sum' else df.resample('H').mean()
    elif interval == 'quarterly':
        # Handle quarterly resampling (consider using 'Q' or custom logic)
        interval_df = df.resample('Q').sum(
        ) if metric == 'sum' else df.resample('Q').mean()
    formatted_results = interval_df.reset_index().rename(
        columns={time_col: 'date'}).to_dict(orient='records')
    return formatted_results


# Get or update the soil data
@app.route("/api/soil_data", methods=["GET", "POST"])
def get_soil_data():
    """Get or Update/Create soil data for specific fields

    Returns:
        list:return list or soil data with their assot fields or redirect to settings page
    """
    if request.method == "GET":
        results = SoilStatus.query.all()
        return [
            r.to_dict(rules=["-field.crop_status", "-field.soil_status"])
            for r in results
        ]
    else:
        data = request.form.to_dict()
        field_query = FieldZone.query.where(FieldZone.id == data["id"]).first()
        soil_status = field_query.soil_status
        del data["id"]
        if soil_status == None:
            soil_status = SoilStatus(field=field_query, **data)
            db.session.add(soil_status)
        else:
            soil_status.soil_type = data['soil_type']
            soil_status.soil_texture = data['soil_texture']
            soil_status.gradient = data['gradient']

            db.session.add(soil_status)
        db.session.commit()
        return redirect("/settings")


# Get or update crop status
@app.route("/api/crops_data", methods=["GET", "POST"])
def get_crops_data():
    """Get or Update/Create crop infor for specific fields

    Returns:
        list:return list or crop infor with their assot fields or redirect to settings page
    """
    if request.method == "GET":
        results = CropsStatus.query.all()
        return [
            r.to_dict(rules=["-field.crop_status", "-field.soil_status"])
            for r in results
        ]
    else:
        data = request.form.to_dict()
        field_query = FieldZone.query.where(FieldZone.id == data["id"]).first()

        crop_status = field_query.crop_status
        del data["id"]
        if crop_status == None:
            crop_status = CropsStatus(field=field_query, **data)
            db.session.add(crop_status)
        else:
            crop_status.crop_name = data['crop_name']
            crop_status.crop_age = data['crop_age']
            crop_status.crop_type = data['crop_type']

            db.session.add(crop_status)
        db.session.commit()
        return redirect("/settings")


# To update and also get fields Zones
@app.route("/api/fields", methods=["GET", "POST"])
def get_fields():
    if request.method == "GET":
        results = FieldZone.query.all()
        return [r.to_dict() for r in results]
    else:
        data = request.form.to_dict()
        field_query = update(FieldZone).where(FieldZone.id == data["id"])
        field_query = field_query.values(**data)
        db.session.execute(field_query)
        db.session.commit()
        return redirect("/settings")


@app.route('/hello')
def hello():
    return jsonify({'message': 'Hello, World!'})

# Home page


@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
@login_required
def index():
    return pages("index")


# docs pages
@app.route("/docs")
@app.route("/docs/")
def doc_root():
    return redirect("/docs/index.html")


@app.route("/docs/<path:filename>")
def docs(filename):
    """Serve static documentation files."""
    return send_from_directory("../docs/_build/", filename)


# Other pages
@app.route("/<page>", methods=["GET"])
@login_required
def pages(page: str):
    """To get a page... any page which maches <page>.html
    ===ToDo: Separate thes pages to have each with its own route..
     Args:
         page (str): Page to get

     Returns:
         _type_: _description_
    """
    if page == "favicon.ico":
        return send_from_directory(app.static_folder, page), 200

    notifications = db.session.execute(
        select(Notifications).limit(4)).scalars()
    notifications = [r.to_dict() for r in notifications]
    r2 = Notifications.query.filter_by(status=False).count()
    data = {}
    data["msgs"] = []
    if len(connected_devices.keys()) < 1:
        data["msgs"].append(
            {
                "msg": "No Component Is connected, Please Check You Components",
                "type": "danger",
            }
        )
    if page == "settings":

        # users=[r.to_dict(rules=['-password']) for r in users]
        fields = FieldZone.query.all()
        data["fields"] = str(
            json.dumps(
                [
                    r.to_dict(
                        rules=["-crop_status.field",
                               "-schedules", "-soil_status.field"]
                    )
                    for r in fields
                ]
            )
        )

        # Add current hardware status
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices_copy.keys()) > 0:
            for k, v in connected_devices_copy.items():
                if "ws" in connected_devices_copy[k]:
                    del connected_devices_copy[k]["ws"]
        data["connected_devices"] = json.dumps(connected_devices_copy)
    elif page == "drainage":
        scheduled_fields = Schedules.query.filter_by(
            status=0, for_="drainage"
        ).all()
        data["scheduled_fields"] = [
            r.to_dict(
                rules=["-field.crop_status",
                       "-field.schedules", "-field.soil_status"]
            )
            for r in scheduled_fields
        ]
        data["scheduled_history"] = [
            r.to_dict() for r in History.query.filter_by(for_="drainage").order_by(desc(History.end_time)).all()
        ]
        for hist_ in data["scheduled_history"]:
            hist_["field"] = FieldZone.query.filter_by(
                id=hist_["field_id"]).first()

        data["auto_schedule"] = "OFF"
        auto = Options.query.get({"option_name": "drainage_auto_schedule"})
        if auto:
            data["auto_schedule"] = auto.option_value

        fields = FieldZone.query.all()
        data["fields"] = [
            r.to_dict(rules=["-crop_status", "-soil_status", "-schedules"])
            for r in fields
        ]
    elif page == "irrigation":

        scheduled_fields = Schedules.query.filter_by(
            status=0, for_="irrigation"
        ).all()
        data["scheduled_fields"] = [
            r.to_dict(
                rules=["-field.crop_status",
                       "-field.schedules", "-field.soil_status"]
            )
            for r in scheduled_fields
        ]
        data["scheduled_history"] = [
            r.to_dict() for r in History.query.filter_by(for_="irrigation").order_by(desc(History.end_time)).all()
        ]
        for hist_ in data["scheduled_history"]:
            hist_["field"] = FieldZone.query.filter_by(
                id=hist_["field_id"]).first()

        data["auto_schedule"] = "OFF"
        auto = Options.query.get({"option_name": "irrigation_auto_schedule"})
        if auto:
            data["auto_schedule"] = auto.option_value

        fields = FieldZone.query.all()
        data["fields"] = [
            r.to_dict(rules=["-crop_status", "-soil_status", "-schedules"])
            for r in fields
        ]
    elif page == "users":
        users = User.query.all()
        data["users"] = users
    elif page == "notifications":
        all_notifications = Notifications.query.all()
        data["all_notifications"] = all_notifications

    data["recommendations"] = get_recommendations()
    return render_template(
        page + ".html",
        page=page,
        notifications=notifications,
        total_notifications=r2,
        **data,
    )


# To add a schedule
@app.route("/api/add_schedule", methods=["POST"])
def add_irrigation_or_drainage_schedule():
    """To add schedule in db

    Returns:
       results after adding
    """
    data = request.form.to_dict()
    schedule_date = datetime.datetime.strptime(
        data["schedule_date"], "%Y-%m-%dT%H:%M")
    scheduler = Schedules(
        duration=data["duration"],
        field_id=data["field_id"],
        schedule_date=schedule_date,
        for_=data["for_"],
    )
    db.session.add(scheduler)
    db.session.commit()
    add_schedule(scheduler)
    # r=Schedules.query.filter_by(id=scheduler.id).first()
    results = scheduler.to_dict(
        rules=["-field.crop_status", "-field.schedules", "-field.soil_status"]
    )
    return results


@app.route("/api/options", methods=["POST", "GET"])
def add_get_update_option():
    """To add/update options

    Returns:
        dict: Option
    """

    if request.method == "GET":
        data = request.args
        return Options.query.get(data["name"]).to_dict()

    data = request.form.to_dict()
    option = Options.query.get(data["name"])
    if not option:
        option = Options(option_name=data["name"], option_value=data["value"])
        db.session.add(option)
    else:
        option.option_value = data["value"]
        db.session.add(option)

    is_on = data["value"] == "ON"
    if data["name"] == "drainage_auto_schedule":
        job = scheduler.get_jobs("auto_drainage_job")
        if is_on:
            if len(job) < 1:
                scheduler.every().seconds.do(
                    start_auto_scheduler_checker, what="drainage"
                ).tag("auto_drainage_job")
        else:
            scheduler.clear("auto_drainage_job")
            start_stop_irrigation_and_drainage(
                what="drainage",
                start=False,
                call_back_fun=update_field_status,
                call_back_args={"what": "drainage", "status": False},
            )

    elif data["name"] == "irrigation_auto_schedule":
        job = scheduler.get_jobs("auto_irrigation_job")
        if is_on:
            if len(job) < 1:
                print("No job")
                scheduler.every().seconds.do(
                    start_auto_scheduler_checker, what="irrigation"
                ).tag("auto_irrigation_job")
        else:
            scheduler.clear("auto_irrigation_job")
            start_stop_irrigation_and_drainage(
                what="irrigation",
                start=False,
                call_back_fun=update_field_status,
                call_back_args={"what": "irrigation", "status": False},
            )
    db.session.commit()
    return option.to_dict()


@app.route("/api/<action>_<what>", methods=["POST"])
def stop_start_irrigation_or_drainage(action, what):
    """To start or stop irrigation and drainage. e.g If one wants to start irrigation should make a POST request to
    /api/start_irrigation, sending data with field_id as id

    Args:
        action (str): start or stop
        what (str): irrigation or drainage

    Returns:
        any: "Done" or "Error",status_code
    """
    if action != "start" and action != "stop":
        return "Error, Action should be start or stop", 404
    if what != "irrigation" and what != "drainage":
        return (
            f"Error! Url should be either /api/{action}_irrigation or /api/{action}_drainage  ",
            404,
        )

    data = request.form.to_dict()

    # Try to send the command to the connected components
    connected_devices_copy = connected_devices.copy()
    # ToDo: To make sure the message is delivered and there is a callback specified
    if len(connected_devices_copy.keys()) > 0:
        if send_command(f"{what} {action}", require_return=True, time_out=20):
            if send_irrigation_stop_start_email(what, action == "start"):
                print(f"Failed to send email for {what}")

            field_query = update(FieldZone).where(
                FieldZone.id == data["field_id"])
            if what == "irrigation":
                field_query = field_query.values(
                    irrigation_status=(action == "start"))
            else:
                field_query = field_query.values(
                    drainage_status=(action == "start"))
            db.session.execute(field_query)
            db.session.commit()
            return "Done"
        else:
            return "Failed", 5000
    else:
        return "No Controlller is connected, check your components!!", 500

    # return "Done"


@app.route("/api/real_time_ecological_factors")
def get_current_ecological_factors():
    return get_all_connected_sensors()


@app.route("/api/refresh_hardware_infor")
def refresh_hardware_infor():
    """To retrieve connected modules infor, including sensors

    Returns:
        _type_: List of components and connected sensors
    """
    return get_all_connected_sensors(True)


# Websocket to get real time hardware infor
@websocket.route("/client/live_hardware_infor")
def refresh_hardware_infor_socket(ws):
    start_time = time.time()
    end_time = time.time()
    connected_devices_copy = connected_devices.copy()
    if len(connected_devices_copy.keys()) > 0:
        for k, v in connected_devices_copy.items():
            if "ws" in connected_devices_copy[k]:
                del connected_devices_copy[k]["ws"]

    ws.send(json.dumps(connected_devices_copy))
    while True:
        if end_time - start_time > 2:
            connected_devices_copy = connected_devices.copy()
            if len(connected_devices_copy.keys()) > 0:
                for k, v in connected_devices_copy.items():
                    if "ws" in connected_devices_copy[k]:
                        del connected_devices_copy[k]["ws"]
            ws.send(json.dumps(connected_devices_copy))
            start_time = time.time()
        end_time = time.time()

    # while True:
    #     data=ws.receive()
    #     data = json.loads(data)
    #     event=data['event']
    #     if event in self.events:
    #         for func in self.events[event]:
    #             func(data['data'],ws)


# Add a schedule
def add_schedule(task: Schedules):
    """Receives a Schedule and checkif it is overdue or not, if not ,
    it adds it to the python schedule instance. This is good as when starting the app, we check if there is any schedule that wasn't executed
    and then execute it..

    Args:
        task (Schedules): Schedule model
    """

    # get the duration of the task
    duration = task.duration

    # is irrigation/drainage
    what = task.for_

    # date to start the irrigation/drainage
    schedule_date = task.schedule_date

    # calculate stop date
    stop_date = schedule_date + timedelta(minutes=duration)
    # Add the start scheduler in scheduler
    current_date = datetime.datetime.now()
    time_format = "%H:%M"
    # date_format = "%d-%m-%Y %H:%M:%S"
    start_in_days = (schedule_date - current_date).days
    stop_in_days = (stop_date - current_date).days

    # Start in days is the number of days from today untill the task executed
    start_in_days = 1 if start_in_days == 0 else start_in_days
    stop_in_days = 1 if stop_in_days == 0 else stop_in_days

    # if the start in days is negative, the schedule is missed
    if start_in_days < 0:
        task.status = 3
        query = update(Schedules).where(Schedules.id == task.id)
        db.session.execute(query)
        db.session.commit()
        # Notify the users about missed scheduler
        msg = f"A schedule  was missed at {schedule_date} , {what} did not start,the system was Offline!!"
        add_notification(msg)
        send_notification_mail("Missed Schedule!!", msg,
                               get_super_and_admin_users_emails())

    else:
        # add task to schedule
        scheduler.every(start_in_days).days.at(schedule_date.strftime(time_format)).do(
            start_stop_irrigation_and_drainage,
            what=what,
            start=True,
            call_back_fun=start_call_back,
            call_back_args=task,
        )
        # Add stop scheduler..... the irrigation should stop at schedule_data+duration(mins)
        scheduler.every(stop_in_days).days.at(stop_date.strftime(time_format)).do(
            start_stop_irrigation_and_drainage,
            what=what,
            start=False,
            call_back_fun=stop_call_back,
            call_back_args=task,
        )

        # Notify users for the schedule
        msg = f"{what} was successfully scheduled at {schedule_date}"
        add_notification(msg)  #add notification to db, to view in the db when users logs in

        #send emails to the adminstrators
        send_notification_mail("New Schedule!!", msg, get_super_and_admin_users_emails())

         
    db.session.commit()


def start_call_back(scheduled_task: Schedules):
    """Function to be called after irrigation or drainage is started through an auto scheduler,
    this function will updated the database on the status of an irrigation, and then notify users that the irrigation/drainage started

    Args:
        scheduled_task (Schedules): Schedules instance from DB_

    Returns:
        CancelJob: Cancel job, not to continue running
    """

    # mark the task as executed
    scheduled_task.status = 1
    # note = Notifications(
    #     f"{scheduled_task.for_} has started at {scheduled_task.schedule_date} succesfully"
    # )
    # db.session.add(note)

    # update database
    field_query = update(FieldZone).where(
        FieldZone.id == scheduled_task.field_id)
    if scheduled_task.for_ == "irrigation":
        field_query = field_query.values(irrigation_status=True)
    else:
        field_query = field_query.values(drainage_status=True)
    db.session.execute(field_query)
    db.session.commit()

    # send notification to the users
    current_time = datetime.datetime.now()
    add_notification(
        f"Scheduled {scheduled_task.for_} started  successfully at {current_time}")
    if send_irrigation_stop_start_email(scheduled_task.for_, True):
        print("Failed to send email for irrigation start")
    return schedule.CancelJob


# check if irr or drainage is on
def is_on(what: str) -> bool:
    """check if irrigation/drainage is currently running or not

    Args:
        what (str):irrigation/drainage

    Returns:
        bool: is on or not
    """
    with app.app_context():
        fields = FieldZone.query.all()
        if what == "irrigation":
            for field in fields:
                if field.irrigation_status:
                    return True
        else:
            for field in fields:
                if field.drainage_status:
                    return True
        return False


def update_field_status(data:dict):
    """Updates the field status about the irrigation/drainage statuses

    Args:
        data (dict): _description_
    """
    with app.app_context():
        
        #what(irrigation/drainage), status(started/stoped)
        what, status = data["what"], data["status"]
        
        #Update the database
        field_query = update(FieldZone).where(FieldZone.name == "Entire Field")
        if what == "irrigation":
            field_query = field_query.values(irrigation_status=status)
        else:
            field_query = field_query.values(drainage_status=status)

        db.session.execute(field_query)
        db.session.commit()
        
        #notify users
        action = "started" if status else "stopped"
        current_time = datetime.datetime.now()
        add_notification(f"{what} {action}  successfully at {current_time}")
        if send_irrigation_stop_start_email(what, status):
            print("Failed to send email for irrigation start")



def start_auto_scheduler_checker(what:str):
    """This is the function to be executed periodical, like each and every minutes to check the current value of the 
    soil moisture, it start at the moment the auto-scheduler is turned on, and stops if toff

    Args:
        what (str): irrigation or drainage
    """
    
    #get the current soil moisture value
    soil_value = get_sensor_value("SoilMoisture")

    #if the value is not None
    if soil_value != None:
        
        #check if irrigation is started(assume what=irrigation)
        is_started = is_on(what)
        
        #start irrigation if value is less than 48
        #if what=drainage, stop it when value is less that 48
        if soil_value < 48:
            if (what == 'irrigation' and (not is_started)):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=True,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": True},
                )
            elif (what == 'drainage' and (is_started)):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=False,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": False},
                )

        elif soil_value > 52:
            # Stop irrigation or drainage if already started
            if (what == 'irrigation' and (is_started)):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=False,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": False},
                )
            elif (what == 'drainage' and (not is_started)):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=True,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": True},
                )


def stop_call_back(scheduled_task: Schedules):
    """Function to be called after irrigation or drainage is started through an auto scheduler,
    it will then updted the status of the scheduler in the DB
    Args:
        scheduled_task (Schedules): Schedules instance from DB_, this is a task which was stopped

    Returns:
        CancelJob: Cancel job, not to continue running
    """
    scheduled_task.status = 0
    
    #get the stop datetime
    stop_date = scheduled_task.schedule_date + timedelta(
        minutes=scheduled_task.duration
    )
    
   #update the db
    field_query = update(FieldZone).where(
        FieldZone.id == scheduled_task.field_id)
    if scheduled_task.for_ == "irrigation":
        field_query = field_query.values(irrigation_status=False)
    else:
        field_query = field_query.values(drainage_status=False)
    db.session.execute(field_query)
    db.session.commit()

    
    #Notify users about the stoped irrigation or drainage
    add_notification(
        f"Scheduled {scheduled_task.for_} stopped  successfully at {stop_date}")
    if send_irrigation_stop_start_email(scheduled_task.for_, False):
        print("Failed to send email for irrigation stop")
        
    #Cancel the job, since executed
    return schedule.CancelJob


def run_pending_schedules():
    """This  function is executed when the app starts, it checks if there are  any schedules in the database. """
    # Get schedules that are in database a run add them on
    with app.app_context():
        
        #get the schedules with status=0 (meaning not executed already)
        schedules = Schedules.query.filter_by(status=0).all()
        for schedule in schedules:
            add_schedule(schedule)
        
        #Check if the irrigation auto schedule is on 
        irr_auto = db.session.query(Options).filter(
            Options.option_name == "irrigation_auto_schedule").first()
        
        #If the irrigation auto schedule is on, start the auto scheduler...
        irrigation_auto_schedule = irr_auto.option_value == "ON" if irr_auto else False
        if irrigation_auto_schedule:
            #here we add the task such that the function start_auto_scheduler_checker, will be called each and every second, to start or stop irrigation
            scheduler.every().seconds.do(
                start_auto_scheduler_checker, what="irrigation"
            ).tag("auto_irrigation_job")

        #check auto-schedule for drainage
        drainage_auto = db.session.query(Options).filter(
            Options.option_name == "drainage_auto_schedule").first()
        drainage_auto_schedule = (
            drainage_auto.option_value == "ON" if drainage_auto else False
        )
        
        #if drainage is on, set the function start_auto_scheduler_checker to be executed after each and every second
        if drainage_auto_schedule:
            scheduler.every().seconds.do(
                start_auto_scheduler_checker, what="drainage"
            ).tag("auto_drainage_job")



######
######This will be executed only, when starting the app
######
with app.app_context():
    
    #create tables if not created already
    db.create_all()
    
    #add the websocket instance for micro-controler
    websocket.init_app(application=app, data_base=db, schedule=scheduler)
    
    #generate sample data
    # build_sample_db(user_bp, user_datastore)
    
    #update db for chnages
    db.session.commit()
    #store the data_store and security to be accessible in other parts of the app
    app.config['USER_DATA_STORE'] = user_datastore
    app.config['SECURITY'] = security
    app.config['SCHEDULER'] = scheduler

    # for f in get_recommendations():
    #     print(f.msg)
    # exit()

