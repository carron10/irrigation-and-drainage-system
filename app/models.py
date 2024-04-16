import math
from dataclasses import dataclass
from datetime import datetime
from random import randint

from flask_security import RoleMixin, UserMixin
from flask_security.utils import hash_password
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func
from sqlalchemy_serializer import SerializerMixin

db = SQLAlchemy()
TABLE_PREFIX = "irrigation_"


class MyModel(db.Model):
    __abstract__ = True

    # Use @declared_attr to dynamically set the table name with prefix
    @declared_attr
    def __tablename__(cls):
        return f"{TABLE_PREFIX}{cls.__name__}".lower()


#Schedule table
class Schedules(MyModel,SerializerMixin):
    """To store irrigation and drainage Schedules

    Args:
        MyModel (_type_): _description_
        SerializerMixin (_type_): _description_
    """
    id = Column(Integer(), primary_key=True)
    duration=Column(Integer,nullable=False)
    time_created=Column(DateTime(timezone=True), server_default=func.now())
    schedule_date=Column(DateTime(timezone=True))
    field_id=Column(Integer, db.ForeignKey(f"{TABLE_PREFIX}fieldzone.id"),nullable=False)
    status=Column(Boolean,default=False)
    for_=Column(String,nullable=False)
    type=Column(String,default="Manual")

    # for
    


# Role Model
class Role(MyModel, RoleMixin):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))


# User Model
class User(MyModel, UserMixin, SerializerMixin):
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255))
    avatar = Column(
        String(255), default="/img/avatars/istockphoto-1337144146-612x612.jpg"
    )
    first_name = Column(String(255))
    last_name = Column(String(255))
    password = Column(String(255), nullable=False)
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    # serialize_only=('roles.id',)
    roles = relationship(
        "Role",
        secondary="irrigation_roles_users",
        backref=backref("users", lazy="dynamic"),
    )
    fs_uniquifier = Column(String(64), unique=True, nullable=False)


# user roles table
roles_users = db.Table(
    "irrigation_roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("irrigation_user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("irrigation_role.id")),
)


# To store meta data for irrigation/drainage/rainfall/ and etc
class Meta(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    meta_key = Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    meta_value = Column(Text, nullable=False)


##Options, to store settings
class Options(MyModel, SerializerMixin):
    option_name = Column(String(100), nullable=False, unique=True,primary_key=True)
    option_value = Column(Text)


##From sensors
class Statistics(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    history_type = Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    value = Column(Text, nullable=False)


# To store data of a certain region/field zone
class FieldZone(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    irrigation_status = Column(Boolean, default=False)
    drainage_status = Column(Boolean, default=False)
    crop_status = relationship("CropsStatus", backref="field", uselist=False)
    schedules = relationship("Schedules", backref="field")
    soil_status = relationship("SoilStatus", backref="field", uselist=False)


class SoilStatus(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    soil_type = Column(String(100))
    soil_texture = Column(String(100))
    gradient = Column(String(100))
    field_id = Column(
        Integer, db.ForeignKey(f"{TABLE_PREFIX}fieldzone.id"), unique=True
    )


class CropsStatus(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    crop_name = Column(String(100), nullable=False, unique=True)
    crop_type = Column(String(100))
    crop_age = Column(Integer)
    field_id = Column(
        Integer, db.ForeignKey(f"{TABLE_PREFIX}fieldzone.id"), unique=True
    )


# To store history for irrigation/drainage/rainfall/ and etc
class History(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)  ##Irrigation or drainage
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    value = Column(Integer)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), server_default=func.now())
    time_spent = Column(DateTime(timezone=True), server_default=func.now())
    field_id = Column(Integer, db.ForeignKey(f"{TABLE_PREFIX}fieldzone.id"))


# Model/Table for notifications
class Notifications(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Boolean(), default=False)
    message = Column(Text(), nullable=False)
    notification_category = Column(String(100), default="Alert")
    notification_icon = Column(String(30), default="bell")

    def __init__(self, message) -> None:
        self.message = message


# Build sample data into database
def build_sample_db(app, user_datastore):
    """
    To generate sample data that can be used for testing and development
    """

    import random
    import string

    db.drop_all()
    db.create_all()

    with app.app_context():
        user_role = Role(name="user")
        super_user_role = Role(name="Admin")
        db.session.add(user_role)
        db.session.add(super_user_role)
        db.session.commit()
        # Generate history data
        for i in range(7):
            for j in range(24 * 2):
                date_ = datetime(2024, 3, 21, math.floor(j / 2), (j % 2) * 30)
                hist_ = (
                    Statistics(
                        for_="RainDrop",
                        history_type="sensor_update",
                        value=randint(50, 90),
                        time_created=date_,
                    ),
                    Statistics(
                        for_="Humidity",
                        history_type="sensor_update",
                        value=randint(50, 90),
                        time_created=date_,
                    ),
                    Statistics(
                        for_="Temperature",
                        history_type="sensor_update",
                        value=randint(50, 90),
                        time_created=date_,
                    ),
                    Statistics(
                        for_="SoilMoisture",
                        history_type="sensor_update",
                        value=randint(50, 90),
                        time_created=date_,
                    ),
                )
                db.session.add_all(hist_)

        note = Notifications("The next irrigation is scheduled for tommorrow at 13:00")
        db.session.add(note)

        fields = (
            FieldZone(name="Entire Field", drainage_status=True),
            FieldZone(name="50CM Downhill from center"),
            FieldZone(name="25cm Pivot"),
            FieldZone(name="50m Uphill From Center"),
        )
        db.session.add_all(fields)

        soil_statuses = (
            SoilStatus(
                field=fields[0],
                soil_type="Clay Soil",
                soil_texture="Clay",
                gradient="2M",
            ),
            SoilStatus(
                field=fields[1],
                soil_type="Loam Soil",
                soil_texture="loamy",
                gradient="3M",
            ),
            SoilStatus(
                field=fields[2],
                soil_type="Sand Soil",
                soil_texture="Sandy",
                gradient="4M",
            ),
            SoilStatus(
                field=fields[3],
                soil_type="Clay Soil",
                soil_texture="Clay",
                gradient="2M",
            ),
        )

        # for i in range(20):
        #     irr_hist = History(
        #         for_="irrigation",
        #         value=randint(100,300),
        #         start_time=1,
        #         end_time=1,
        #         time_spent=1,
        #         # field_id=1,
        #     )
        #     drainage_hist = History(
        #         for_="irrigation",
        #         value=randint(100,300),
        #         start_time=1,
        #         end_time=1,
        #         time_spent=1,
        #         # field_id=1,
        #     )
        #     db.session.add(drainage_hist)
        #     db.session.add(irr_hist)
            
        db.session.add_all(soil_statuses)
        crop_statuses = CropsStatus(
            field=fields[0], crop_type="Just", crop_name="Maize", crop_age=20
        )
        db.session.add(crop_statuses)
        admin_usr = user_datastore.create_user(
            first_name="Carron Muleya",
            email="carronmuleya10@gmail.com",
            password=hash_password("QKBhvm6qeUJuHQ@"),
            roles=[user_role, super_user_role],
        )
        db.session.commit()
    return
