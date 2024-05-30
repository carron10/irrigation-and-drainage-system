import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import calendar
from random import randint
import numpy as np
from flask_security import RoleMixin, UserMixin
from flask_security.utils import hash_password
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String, JSON,
                        Text)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship
# from sqlalchemy.sql import func
from sqlalchemy_serializer import SerializerMixin

db = SQLAlchemy()
TABLE_PREFIX = f"irrigation_"


class MyModel(db.Model):
    __abstract__ = True

    # Use @declared_attr to dynamically set the table name with prefix
    @declared_attr
    def __tablename__(cls):
        return f"{TABLE_PREFIX}{cls.__name__}".lower()


# Schedule table
class Schedules(MyModel, SerializerMixin):
    """To store irrigation and drainage Schedules

    Args:
        MyModel (_type_): _description_
        SerializerMixin (_type_): _description_
    """
    id = Column(Integer(), primary_key=True)
    duration = Column(Integer, nullable=False)
    time_created = Column(DateTime(
        timezone=True), server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
    schedule_date = Column(DateTime(timezone=True))
    field_id = Column(Integer, db.ForeignKey(
        f"{TABLE_PREFIX}fieldzone.id"), nullable=False)
    status = Column(Boolean, default=False)  # Executed or Not
    for_ = Column(String, nullable=False)  # For irrigation or drainage
    type = Column(String, default="Manual")

    # for


class UserCaps(MyModel):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

# Role Model


class Role(MyModel, RoleMixin,SerializerMixin):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True, default="user")
    description = Column(String(255))
    permissions = Column(JSON)
    caps = relationship(
        "UserCaps",
        secondary=f"{TABLE_PREFIX}roles_caps",
        backref=backref("roles", lazy="dynamic"),
    )

    def add_permission(self, *permissions: str):
        """Add permissions to the role."""
        self.permissions.extend(permissions)

    def add_cap(self, name, description=None):
        cap = UserCaps(name=name, description=description)
        db.session.add(cap)

    def assign_cap(self, cap: UserCaps):
        self.caps.append(cap)

    def has_permision(self, permission: str):
        return permission in self.get_permissions()


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
        secondary=f"{TABLE_PREFIX}roles_users",
        backref=backref("users", lazy="dynamic"),
    )
    caps = relationship(
        "UserCaps",
        secondary=f"{TABLE_PREFIX}user_caps",
        backref=backref("users", lazy="dynamic"),
    )
    fs_uniquifier = Column(String(64), unique=True, nullable=False)

    def is_super_user(self):
        """
        Check if the user is a super user.
        """
        
        return self.has_role("super")

    def is_admin(self):
        """
        Check if the user is a super user.
        """
        return self.has_role("admin")

    def has_role(self, role_name: str):
        """
    Check if the user has the specified role.
        """
        for role in self.roles:
            if role.name == role_name:
                return True
        return False

    def has_cap(self, cap: str):
        if self.has_permission(cap):
            return True
        for cp in self.caps:
            if cp.name == cap:
                return True
        return False

    def has_permission(self, permission: str):
        for role in self.roles:
            if role.has_permission(permission):
                return True
        return False


roles_caps = db.Table(
    f"{TABLE_PREFIX}roles_caps",
    db.Column("caps_id", db.Integer(), db.ForeignKey(
        f"{TABLE_PREFIX}usercaps.id")),
    db.Column("role_id", db.Integer(),
              db.ForeignKey(f"{TABLE_PREFIX}role.id")),
)
user_caps = db.Table(
    f"{TABLE_PREFIX}user_caps",
    db.Column("caps_id", db.Integer(), db.ForeignKey(
        f"{TABLE_PREFIX}usercaps.id")),
    db.Column("user_id", db.Integer(),
              db.ForeignKey(f"{TABLE_PREFIX}user.id")),
)
# user roles table
roles_users = db.Table(
    f"{TABLE_PREFIX}roles_users",
    db.Column("user_id", db.Integer(),
              db.ForeignKey(f"{TABLE_PREFIX}user.id")),
    db.Column("role_id", db.Integer(),
              db.ForeignKey(f"{TABLE_PREFIX}role.id")),
)


# To store meta data for irrigation/drainage/rainfall/ and etc
class Meta(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    meta_key = Column(String(100))
    time_created = Column(DateTime(
        timezone=True), server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
    meta_value = Column(Text, nullable=False)


# Options, to store settings
class Options(MyModel, SerializerMixin):
    option_name = Column(String(100), nullable=False,
                         unique=True, primary_key=True)
    option_value = Column(Text)


# From sensors
class Statistics(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    history_type = Column(String(100))
    time_created = Column(DateTime(
        timezone=True), server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
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
    for_ = Column(String(100), nullable=False)  # Irrigation or drainage
    time_created = Column(DateTime(timezone=True), server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
    value = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True),
                        server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
    end_time = Column(DateTime(timezone=True))
    time_spent = Column(Integer, nullable=False)
    field_id = Column(Integer, db.ForeignKey(
        f"{TABLE_PREFIX}fieldzone.id"), nullable=False, )


# Model/Table for notifications
class Notifications(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    time_created = Column(DateTime(
        timezone=True), server_default=datetime.now().strftime("%Y-%m-%dT%H:%M"))
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

    # Generate irrigation history

    fields = (
        FieldZone(name="Entire Field"),
        FieldZone(name="50CM Downhill from center"),
        FieldZone(name="25cm Pivot"),
        FieldZone(name="50m Uphill From Center"),
    )
    db.session.add_all(fields)
    db.session.commit()

    # Generate data for irrigation and drainage
    start_date = datetime(2015, 1, 1).date()
    end_date = datetime(2024, 1, 1).date()
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    for task in ["irrigation", "drainage"]:
        for year in range(start_date.year, end_date.year + 1):
            for month in range(1,12):
                # Get the number of days in the month
                num_days = calendar.monthrange(year, month)[1]

                # Randomly select 60% of days in the month
                days = np.random.choice(range(1, num_days + 1), int(num_days * 0.6))

                for day in days:
                    start_time=datetime(year, month, day,randint(0,23),randint(0,59))
                    time_spent_hrs=randint(2,6)
                    end_ = start_time+timedelta(hours=time_spent_hrs)
                    _history = History(field_id=fields[randint(0, 3)].id, for_=task, value=randint(
                        100, 500), time_spent=time_spent_hrs, end_time=end_,start_time=start_time)
                    db.session.add(_history)

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
    db.session.add_all(soil_statuses)
    crop_statuses = CropsStatus(
        field=fields[0], crop_type="Just", crop_name="Maize", crop_age=20
    )
    db.session.add(crop_statuses)
    db.session.commit()
    return
