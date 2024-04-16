import datetime
import json
import os
import time

import psycopg2
from flask import (Blueprint, Flask, Response, current_app, jsonify, redirect,
                   render_template, request, send_from_directory, url_for)
from flask_security import (Security, SQLAlchemyUserDatastore, current_user,
                            login_required)
from flask_security.forms import RegisterForm, Required, StringField
from flask_security.utils import hash_password
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Table, select, update
from sqlalchemy.ext.declarative import declared_attr

from app import create_app
from app.micro_controllers_ws_server import (connected_devices,
                                             get_all_connected_sensors,
                                             websocket)
from app.models import (CropsStatus, FieldZone, Meta, MyModel, Notifications,
                        Options, Role, Schedules, SoilStatus, Statistics, User,
                        build_sample_db, db)
from app.websocket.flask_sock import Sock

app = create_app()


app.config["SQLALCHEMY_MODEL_BASE_CLASS"] = MyModel
db.init_app(app)

# Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


# extend fields for registration form
class ExtendedRegisterForm(RegisterForm):
    first_name = StringField("First Name", [Required()])
    last_name = StringField("Last Name", [Required()])


# security
security = Security(app, user_datastore, register_form=ExtendedRegisterForm)
#######Setup url route#####


# Function to execute when one visit /api/notifications
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    limit = request.args.get("limit")
    if not limit:
        limit = 20
    results = db.session.execute(select(Notifications).limit(limit)).scalars()
    return [r.to_dict() for r in results]


# Returns users registered in this app
# Accep limit as int, which specifies the limit of users to return
@app.route("/api/users", methods=["GET"])
def get_users():
    limit = request.args.get("limit")
    if not limit:
        limit = 20
    results = User.query.limit(limit).all()
    return [r.to_dict(rules=["-password"]) for r in results]


@app.route("/api/history", methods=["GET"])
def get_history():
    results = Statistics.query.all()
    return [r.to_dict() for r in results]


@app.route("/api/soil_data", methods=["GET", "POST"])
def get_soil_data():
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
        print(data)
        field_query = update(FieldZone).where(FieldZone.id == data["id"])
        field_query = field_query.values(**data)
        db.session.execute(field_query)
        db.session.commit()
        return redirect("/settings")


##Home page
@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
@login_required
def hello():
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
def pages(page):
    if page == "favicon.ico":
        return send_from_directory(app.static_folder, page), 200

    notifications = db.session.execute(select(Notifications).limit(4)).scalars()
    # notifications = [r.to_dict() for r in results]
    r2 = Notifications.query.filter_by(status=False).count()
    data = {}
    if page == "settings":
        users = User.query.all()
        # users=[r.to_dict(rules=['-password']) for r in users]
        fields = FieldZone.query.all()
        data["fields"] = str(
            json.dumps(
                [
                    r.to_dict(rules=["-crop_status.field","-schedules", "-soil_status.field"])
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
        fields = FieldZone.query.all()
        data["fields"] = [
            r.to_dict(rules=["-crop_status", "-soil_status","-schedules"]) for r in fields
        ]
    elif page == "irrigation":
        scheduled_fields = Schedules.query.filter_by(status=False).all()
        data["scheduled_fields"] = [
            r.to_dict(rules=["-field.crop_status","-field.schedules", "-field.soil_status"]) for r in scheduled_fields
        ]
        
        data['auto_schedule']=Options.query.get({'option_name':"irrigation_auto_schedule"}).option_value
        
        print(data['auto_schedule'])
        fields= FieldZone.query.all()
        data["fields"] = [
            r.to_dict(rules=["-crop_status", "-soil_status","-schedules"]) for r in fields
        ]
    return render_template(
        page + ".html",
        page=page,
        notifications=notifications,
        total_notifications=r2,
        **data,
    )




@app.route("/api/add_irrigation_schedule",methods=['POST'])
def add_irrigation_schedule():
    data=request.form.to_dict()
    schedule_date=datetime.datetime.strptime(data['schedule_date'],"%Y-%m-%dT%H:%M")
    schedule=Schedules(duration=data['duration'],field_id=data['field_id'],schedule_date=schedule_date,for_="irrigation")
    db.session.add(schedule)
    db.session.commit()
    # r=Schedules.query.filter_by(id=schedule.id).first()
    results= schedule.to_dict(rules=["-field.crop_status","-field.schedules", "-field.soil_status"])
    return results


@app.route("/api/options",methods=['POST',"GET"])
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
            option = Options(option_name=data['name'],option_value=data['value'])
            db.session.add(option)
    else:
            option.option_value=data['value']
            db.session.add(option)
    db.session.commit()
    return option.to_dict()

@app.route("/api/start_irrigation/<action>",methods=['POST'])
def stop_or_start_irrigation(action):
    if action != "start" and action != "stop":
        return "Error, Action should be start or stop", 404
    data = request.form.to_dict()
    try:
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices_copy.keys()) > 0:
            for k, v in connected_devices_copy.items():
                connected_devices_copy[k]["ws"].send(
                    json.dumps(
                        {
                            "data": {"cmd": f"irrigation {action}"},
                            "event": "command",
                        }
                    )
                )
            field_query = update(FieldZone).where(FieldZone.id == data["id"])
            field_query = field_query.values(irrigation_status=action=="start")
            db.session.execute(field_query)
            db.session.commit()
        else:
            return "No Controlller is connected, check your components!!", 500

    except Exception as ex:
        return ex, 5000

    return "Done"


@app.route("/api/real_time_ecological_factors")
def get_current_ecological_factors():
    return get_all_connected_sensors()


@app.route("/api/refresh_hardware_infor")
def refresh_hardware_infor():
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


with app.app_context():
    db.create_all()
    websocket.init_app(application=app, data_base=db)
    ##Remove this to avoid generating sample data
    app_dir = os.path.realpath(os.path.dirname(__file__))
    dataBase_path = os.path.join(app_dir, app.config["DATABASE_FILE"])
    if not os.path.exists(dataBase_path):
        # build_sample_db(app=app, user_datastore=user_datastore)
        pass
