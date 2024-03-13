import os
import json
import time
import psycopg2
from flask import (
    Flask,
    url_for,
    redirect,
    render_template,
    request,
    jsonify,
    send_from_directory,
)
from flask_security.utils import hash_password
from sqlalchemy import select, update
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required,
)
from flask_security.forms import RegisterForm
from flask_security.forms import StringField
from flask_security.forms import Required
from app import create_app
from app.models import (
    db,
    User,
    Role,
    Notifications,
    Options,
    Statistics,
    Meta,
    FieldZone,
    build_sample_db,MyModel
)
from app.micro_controllers_ws_server import websocket, connected_devices,get_all_connected_sensors
from flask import Blueprint, request, Response, current_app
from app.websocket.flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, MetaData
from sqlalchemy.ext.declarative import declared_attr



app = create_app()
app.config['SQLALCHEMY_MODEL_BASE_CLASS'] = MyModel
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
        data["fields"] = str(json.dumps([r.to_dict() for r in fields]))
        data["users"] = users

        ##Add current hardware status
        connected_devices_copy = connected_devices.copy()
        if len(connected_devices_copy.keys()) > 0:
            for k, v in connected_devices_copy.items():
                if "ws" in connected_devices_copy[k]:
                    del connected_devices_copy[k]["ws"]
        data['connected_devices']=json.dumps(connected_devices_copy)
    return render_template(
        page + ".html",
        page=page,
        notifications=notifications,
        total_notifications=r2,
        **data
    )


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
        pass
        build_sample_db(app=app,user_datastore=user_datastore)
