import os
import json 
import psycopg2
from flask import Flask, url_for, redirect, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, current_user, login_required
from flask_security.utils import hash_password
from flask_security.forms import RegisterForm
from flask_security.forms import StringField
from flask_security.forms import Required
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Boolean, DateTime, Column, Integer, \
    String, ForeignKey, Text, select,update

from dataclasses import dataclass
from sqlalchemy_serializer import SerializerMixin

# Create Flask application
app = Flask(__name__,static_url_path='',static_folder='static',template_folder='templates')


#Configuration
app.config.from_pyfile('config.py')

#Create Database instance
db = SQLAlchemy(app)


# Define models

#user roles table
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# Role Model
class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

# User Model
class User(db.Model, UserMixin,SerializerMixin):
    __tablename__ = 'user'
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
    roles = relationship('Role', secondary='roles_users',
                         backref=backref('users', lazy='dynamic'))
    fs_uniquifier = Column(String(64), unique=True, nullable=False)
   

#To store meta data for irrigation/drainage/rainfall/ and etc
class Meta(db.Model, SerializerMixin):
    __tablename__ = 'meta_data'
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    meta_key=Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    meta_value = Column(Text, nullable=False)

##Options, to store settings
class Options(db.Model, SerializerMixin):
    __tablename__ = 'options'
    id = Column(Integer, primary_key=True)
    option_name= Column(String(100), nullable=False,unique=True)
    option_value=Column(Text)

#To store history for irrigation/drainage/rainfall/ and etc
class Statistics(db.Model, SerializerMixin):
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True)
    for_ = Column(String(100), nullable=False)
    history_type=Column(String(100))
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    value = Column(Text, nullable=False)
    
# To store data of a certain region/field zone
class FieldZone(db.Model, SerializerMixin):
    __tablename__ = 'field_zone'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False,unique=True)
    soil_type = Column(String(100))
    soil_texture = Column(String(100))
    gradient = Column(String(100))



# Model/Table for notifications
class Notifications(db.Model, SerializerMixin):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Boolean(), default=False)
    message = Column(Text(), nullable=False)
    notification_category = Column(String(100), default="Alert")
    notification_icon = Column(String(30), default="bell")

    def __init__(self, message) -> None:
        self.message = message





# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


#extend fields for registration form
class ExtendedRegisterForm(RegisterForm):
    first_name = StringField('First Name', [Required()])
    last_name = StringField('Last Name', [Required()])

#security 
security = Security(app, user_datastore,
                    register_form=ExtendedRegisterForm)


#######Setup url route#####

#Function to execute when one visit /api/notifications
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    limit = request.args.get('limit')
    if not limit:
        limit = 20
    results = db.session.execute(select(Notifications).limit(limit)).scalars()
    return [r.to_dict() for r in results]

# Returns users registered in this app
# Accep limit as int, which specifies the limit of users to return
@app.route('/api/users', methods=['GET'])
def get_users():
    limit = request.args.get('limit')
    if not limit:
        limit = 20
    results = User.query.limit(limit).all()
    return [r.to_dict(rules=['-password']) for r in results]

#To update and also get fields Zones
@app.route('/api/fields', methods=['GET',"POST"])
def get_fields():
    if request.method=="GET":
        results = FieldZone.query.all()
        return [r.to_dict() for r in results]
    else:
        data=request.form.to_dict()
        print(data)
        field_query=update(FieldZone).where(FieldZone.id==data['id'])
        field_query= field_query.values(**data)
        db.session.execute(field_query)
        db.session.commit()
        return redirect('/settings')


##Home page
@app.route("/",methods=["GET"])
@app.route("/index.html",methods=["GET"])
@login_required
def hello():
    return pages('index')


#Other pages
@app.route("/<page>",methods=["GET"])
@login_required
def pages(page):
    notifications= db.session.execute(select(Notifications).limit(4)).scalars()
    # notifications = [r.to_dict() for r in results]
    r2 = Notifications.query.filter_by(status=False).count()
    data={}
    if page=="settings":
        users = User.query.all()
        # users=[r.to_dict(rules=['-password']) for r in users]
        fields = FieldZone.query.all()
        data['fields']=str(json.dumps([r.to_dict() for r in fields]))
        data['users']=users
    return render_template(page+'.html',
                           page=page, notifications=notifications, total_notifications=r2,**data)



#Build sample data into database
def build_sample_db():
    """
    Populate a small db with some example entries.
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


if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    dataBase_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    # if not os.path.exists(dataBase_path):
    #     with app.app_context():
    #         build_sample_db()

    # Start app
    app.run(debug=True)
