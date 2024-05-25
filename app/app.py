import datetime
from datetime import timedelta
import json
import os
import time
from schedule import Scheduler
import psycopg2
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
from sqlalchemy import MetaData, Table, select, update
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
import schedule
from app.utils import generate_unique_string
from app.user_routes import user_bp,security,user_datastore
from flask_mailman import Mail

app = create_app()

app.register_blueprint(user_bp)

security.init_app(app)

app.config["SQLALCHEMY_MODEL_BASE_CLASS"] = MyModel
scheduler = Scheduler()
# app.config["SCHEDULER"] = scheduler
db.init_app(app)

mail = Mail(app)


@app.before_request
def before_request_handler():
    if request.path == '/login' and request.method == 'GET':
        if User.query.count() == 0:
            # If no users exist, redirect to setup route
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
    return [r.to_dict(rules=["-password"]) for r in results]


@app.route("/api/history/<for_>", methods=["GET"])
def get_history(for_):
    """Return sensoers reading history

    Returns:
        _type_: _description_
    """
    results = Statistics.query.all()
    return [r.to_dict() for r in results]


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
            soil_status = soil_status.values(**data)
            db.session.execute(soil_status)
        db.session.commit()
        return redirect("/settings")


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
            crop_status = crop_status.values(**data)
            db.session.execute(crop_status)
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

##Home page
@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
@login_required
def index():
    return pages("index")


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
    print("shh")
    """To get a page... any page which maches <page>.html
    ===ToDo: Separate thes pages to have each with its own route..
     Args:
         page (str): Page to get

     Returns:
         _type_: _description_
    """
    if page == "favicon.ico":
        return send_from_directory(app.static_folder, page), 200

    notifications = db.session.execute(select(Notifications).limit(4)).scalars()
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
        users = User.query.all()
        # users=[r.to_dict(rules=['-password']) for r in users]
        fields = FieldZone.query.all()
        data["fields"] = str(
            json.dumps(
                [
                    r.to_dict(
                        rules=["-crop_status.field", "-schedules", "-soil_status.field"]
                    )
                    for r in fields
                ]
            )
        )
        data["users"] = users

        ##Add current hardware status
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices_copy.keys()) > 0:
            for k, v in connected_devices_copy.items():
                if "ws" in connected_devices_copy[k]:
                    del connected_devices_copy[k]["ws"]
        data["connected_devices"] = json.dumps(connected_devices_copy)
    elif page == "drainage":
        scheduled_fields = Schedules.query.filter_by(
            status=False, for_="drainage"
        ).all()
        data["scheduled_fields"] = [
            r.to_dict(
                rules=["-field.crop_status", "-field.schedules", "-field.soil_status"]
            )
            for r in scheduled_fields
        ]
        data["scheduled_history"] = [
            r.to_dict() for r in History.query.filter_by(for_="drainage").all()
        ]
        for hist_ in data["scheduled_history"]:
            hist_["field"] = FieldZone.query.filter_by(id=hist_["field_id"]).first()

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
            status=False, for_="irrigation"
        ).all()
        data["scheduled_fields"] = [
            r.to_dict(
                rules=["-field.crop_status", "-field.schedules", "-field.soil_status"]
            )
            for r in scheduled_fields
        ]
        data["scheduled_history"] = [
            r.to_dict() for r in History.query.filter_by(for_="irrigation").all()
        ]
        for hist_ in data["scheduled_history"]:
            hist_["field"] = FieldZone.query.filter_by(id=hist_["field_id"]).first()

        data["auto_schedule"] = "OFF"
        auto = Options.query.get({"option_name": "irrigation_auto_schedule"})
        if auto:
            data["auto_schedule"] = auto.option_value

        fields = FieldZone.query.all()
        data["fields"] = [
            r.to_dict(rules=["-crop_status", "-soil_status", "-schedules"])
            for r in fields
        ]

    return render_template(
        page + ".html",
        page=page,
        notifications=notifications,
        total_notifications=r2,
        **data,
    )


@app.route("/api/add_schedule", methods=["POST"])
def add_irrigation_or_drainage_schedule():
    data = request.form.to_dict()
    schedule_date = datetime.datetime.strptime(data["schedule_date"], "%Y-%m-%dT%H:%M")
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
            field_query = update(FieldZone).where(FieldZone.id == data["field_id"])
            if what == "irrigation":
                field_query = field_query.values(irrigation_status=(action == "start"))
            else:
                field_query = field_query.values(drainage_status=(action == "start"))
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
    connected_devices_copy = connected_devices.copy()
    if len(connected_devices_copy.keys()) > 0:
        for k, v in connected_devices_copy.items():
            if "ws" in connected_devices_copy[k]:
                del connected_devices_copy[k]["ws"]
    return connected_devices_copy


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


def add_schedule(task: Schedules):
    duration = task.duration
    what = task.for_
    schedule_date = task.schedule_date
    stop_date = schedule_date + timedelta(minutes=duration)
    ##Add the start scheduler in scheduler
    current_date = datetime.datetime.now()
    time_format = "%H:%M"
    # date_format = "%d-%m-%Y %H:%M:%S"
    start_in_days = (schedule_date - current_date).days
    stop_in_days = (stop_date - current_date).days

    # print(
    #     f"New Job Days {stop_in_days}  {start_in_days} start=={schedule_date.strftime(time_format)} stop=={stop_date.strftime(time_format)}"
    # )

    start_in_days = 1 if start_in_days == 0 else start_in_days
    stop_in_days = 1 if stop_in_days == 0 else stop_in_days

    if start_in_days < 0:
        ##Notify the users about missed scheduler
        note = Notifications(
            f"A scheduler  was missed at {schedule_date} , maybe the {what} started but the System was offline"
        )
        db.session.add(note)
        db.session.commit()
    else:
        scheduler.every(start_in_days).days.at(schedule_date.strftime(time_format)).do(
            start_stop_irrigation_and_drainage,
            what=what,
            start=True,
            call_back_fun=start_call_back,
            call_back_args=task,
        )
        ##Add stop scheduler..... the irrigation should stop at schedule_data+duration(mins)
        scheduler.every(stop_in_days).days.at(stop_date.strftime(time_format)).do(
            start_stop_irrigation_and_drainage,
            what=what,
            start=False,
            call_back_fun=stop_call_back,
            call_back_args=task,
        )
        note = Notifications(f"{what} was successfully scheduled at {schedule_date}")
        db.session.add(note)
    db.session.commit()


def start_call_back(scheduled_task: Schedules):
    """Function to be called after irrigation or drainage is started through an auto scheduler,
    this function will updated the database on the status of an irrigation

    Args:
        scheduled_task (Schedules): Schedules instance from DB_

    Returns:
        CancelJob: Cancel job, not to continue running
    """
    scheduled_task.status = True
    note = Notifications(
        f"{scheduled_task.for_} has started at {scheduled_task.schedule_date} succesfully"
    )
    db.session.add(note)
    field_query = update(FieldZone).where(FieldZone.id == scheduled_task.field_id)
    if scheduled_task.for_ == "irrigation":
        field_query = field_query.values(irrigation_status=True)
    else:
        field_query = field_query.values(drainage_status=True)
    db.session.execute(field_query)
    db.session.commit()
    return schedule.CancelJob


# check if irr or drainage is on
def is_on(what):
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


def update_field_status(data):
    what, status = data["what"], data["status"]
    field_query = update(FieldZone).where(FieldZone.name == "Entire Field")
    if what == "irrigation":
        field_query = field_query.values(irrigation_status=status)
    else:
        field_query = field_query.values(drainage_status=status)

    db.session.execute(field_query)
    db.session.commit()


def start_auto_scheduler_checker(what):
    soil_value = get_sensor_value("SoilMoisture")
    if soil_value != None:
        if soil_value < 48:
            # Start irrigation
            if not is_on(what):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=True,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": True},
                )
        elif soil_value > 52:
            # Stop irrigation or drainage if already started
            if is_on(what):
                start_stop_irrigation_and_drainage(
                    what=what,
                    start=False,
                    call_back_fun=update_field_status,
                    call_back_args={"what": what, "status": False},
                )


def stop_call_back(scheduled_task: Schedules):
    """Function to be called after irrigation or drainage is started through an auto scheduler,
    it will then updted the status of the scheduler in the DB
    Args:
        scheduled_task (Schedules): Schedules instance from DB_

    Returns:
        CancelJob: Cancel job, not to continue running
    """
    scheduled_task.status = False
    stop_date = scheduled_task.schedule_date + timedelta(
        minutes=scheduled_task.duration
    )
    note = Notifications(f"{scheduled_task.for_} has ended  at {stop_date}")
    db.session.add(note)
    field_query = update(FieldZone).where(FieldZone.id == scheduled_task.field_id)
    if scheduled_task.for_ == "irrigation":
        field_query = field_query.values(irrigation_status=False)
    else:
        field_query = field_query.values(drainage_status=False)
    db.session.execute(field_query)
    db.session.commit()
    return schedule.CancelJob

def run_pending_schedules():
    global thread_running
<<<<<<< HEAD
    print("Hello world")
=======
    print("Started")
>>>>>>> 3ee5dbbcb52d776050f7b99cbbd1682bc87a7107
    """To run Irrigation, Drainage many more schedules"""
    ##Get schedules that are in database a run add them on
    with app.app_context():
        schedules = Schedules.query.filter_by(status=False).all()
        for schedul in schedules:
            add_schedule(schedul)

        irr_auto =db.session.query(Options).filter(Options.option_name == "irrigation_auto_schedule").first()
        # Options.query.get({"option_name": "irrigation_auto_schedule"})
        irrigation_auto_schedule = irr_auto.option_value == "ON" if irr_auto else False
        if irrigation_auto_schedule:
            scheduler.every().seconds.do(
                start_auto_scheduler_checker, what="irrigation"
            ).tag("auto_irrigation_job")
        drainage_auto = db.session.query(Options).filter(Options.option_name == "drainage_auto_schedule").first() #Options.query.get({"option_name": "drainage_auto_schedule"})
        drainage_auto_schedule = (
            drainage_auto.option_value == "ON" if drainage_auto else False
        )
        if drainage_auto_schedule:
            scheduler.every().seconds.do(
                start_auto_scheduler_checker, what="drainage"
            ).tag("auto_drainage_job")

        while thread_running:
<<<<<<< HEAD
            print("run pend")
=======
>>>>>>> 3ee5dbbcb52d776050f7b99cbbd1682bc87a7107
            scheduler.run_pending()
            time.sleep(1)


with app.app_context():
    db.create_all()
    websocket.init_app(application=app, data_base=db, schedule=scheduler)
    
    db.session.commit()
    

# Flag to indicate if the thread is running
thread_running = False

# Global reference to the thread
mythread = None
@app.teardown_appcontext
def shutdown_thread(exception):
    global thread_running, mythread

    # Stop the thread
    thread_running = False

    # Wait for the thread to exit
    if mythread and mythread.is_alive():
        mythread.join()


<<<<<<< HEAD
=======
# Flag to indicate if the thread is running
thread_running = False

# Global reference to the thread
mythread = None
@app.teardown_appcontext
def shutdown_thread(exception):
    global thread_running, mythread

    # Stop the thread
    thread_running = False

    # Wait for the thread to exit
    if mythread and mythread.is_alive():
        mythread.join()


>>>>>>> 3ee5dbbcb52d776050f7b99cbbd1682bc87a7107
