from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DateTime, Column, Integer, \
    String, ForeignKey, Text
from flask_security import UserMixin, RoleMixin
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import relationship, backref
from dataclasses import dataclass
from sqlalchemy.sql import func
from flask_security.utils import hash_password
from sqlalchemy.ext.declarative import declared_attr

db = SQLAlchemy()
TABLE_PREFIX="irrigation_"
class MyModel(db.Model):
  __abstract__ = True
  # Use @declared_attr to dynamically set the table name with prefix
  @declared_attr
  def __tablename__(cls):
    return f"{TABLE_PREFIX}{cls.__name__}".lower()





# Define models


# Role Model
class Role(MyModel, RoleMixin):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

# User Model
class User(MyModel, UserMixin,SerializerMixin):
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255))
    avatar = Column(
        String(255), default="/img/avatars/istockphoto-1337144146-612x612.jpg")
    first_name = Column(String(255))
    last_name = Column(String(255))
    password = Column(String(255),nullable=False)
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    # serialize_only=('roles.id',)
    roles = relationship('Role', secondary='irrigation_roles_users',
                         backref=backref('users', lazy='dynamic'))
    fs_uniquifier = Column(String(64), unique=True, nullable=False)
   
#user roles table
roles_users = db.Table(
    'irrigation_roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('irrigation_user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('irrigation_role.id'))
)

#To store meta data for irrigation/drainage/rainfall/ and etc
class Meta(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    meta_key=Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    meta_value = Column(Text, nullable=False)

##Options, to store settings
class Options(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    option_name= Column(String(100), nullable=False,unique=True)
    option_value=Column(Text)

#To store history for irrigation/drainage/rainfall/ and etc
class Statistics(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    history_type=Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    value = Column(Text, nullable=False)
    
# To store data of a certain region/field zone
class FieldZone(MyModel, SerializerMixin):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False,unique=True)
    soil_type = Column(String(100))
    soil_texture = Column(String(100))
    gradient = Column(String(100))

#Todo:  Add solit data and crop type tables



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



#Build sample data into database
def build_sample_db(app, user_datastore):
    
    
    """
    To generate sample data that can be used for testing and development
    """

    import string
    import random

    db.drop_all()
    db.create_all()

    with app.app_context():
        user_role = Role(name='user')
        super_user_role = Role(name='superuser')
        db.session.add(user_role)
        db.session.add(super_user_role)
        db.session.commit()

       
        note = Notifications(
            "The next irrigation is scheduled for tommorrow at 13:00")
        db.session.add(note)

        fields= FieldZone(name="Entire Field",soil_type="Clay Soil",soil_texture="Clay",gradient="2M"),FieldZone(name="50CM Downhill from center",soil_type="Loam Soil",soil_texture="loamy",gradient="3M"),FieldZone(name="25cm Pivot",soil_type="Sand Soil",soil_texture="Sandy",gradient="4M"),FieldZone(name="50m Uphill From Center",soil_type="Clay Soil",soil_texture="Clay",gradient="2M"),
        db.session.add_all(fields)
        db.session.add_all(fields)

        test_user = user_datastore.create_user(
            first_name='Admin',
            email='admin@example.com',
            password=hash_password('admin'),
            roles=[user_role, super_user_role]
        )
        admin_usr = user_datastore.create_user(
            first_name='Carron Muleya',
            email='carronmuleya10@gmail.com',
            password=hash_password('QKBhvm6qeUJuHQ@'),
            roles=[user_role, super_user_role]
        )
        db.session.commit()
    return


