import os
import json
import time 
import psycopg2
from flask import Flask, url_for, redirect, render_template, request, jsonify,send_from_directory
from flask_security.utils import hash_password
from sqlalchemy import select,update
from flask_security import Security, SQLAlchemyUserDatastore, current_user, login_required
from flask_security.forms import RegisterForm
from flask_security.forms import StringField
from flask_security.forms import Required
from app import create_app
from app.models import db,User,Role,Notifications,Options,Statistics,Meta,FieldZone
from app.micro_controllers_ws_server  import websocket
from flask import Blueprint, request, Response, current_app

app = create_app()
db.init_app(app)


#Security 
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

@app.route('/docs')
@app.route('/docs/')
def doc_root():
    return redirect("/docs/index.html")
@app.route('/docs/<path:filename>')
def docs(filename):
    """Serve static documentation files."""
    return send_from_directory(
        "../docs/_build/",
        filename
        )

#Other pages
@app.route("/<page>",methods=["GET"])
@login_required
def pages(page):
    if page=="favicon.ico":
        return send_from_directory(app.static_folder, page),200
    
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








with app.app_context():
    websocket.init_app(app)
    db.create_all()


# if __name__ == '__main__':

#     # Build a sample db on the fly, if one does not exist yet.
#     app_dir = os.path.realpath(os.path.dirname(__file__))
#     dataBase_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
#     # if not os.path.exists(dataBase_path):
#     #     with app.app_context():
#     #         build_sample_db()

#     # Start app
#     app.run(debug=True)
