from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required
)
from flask_security.utils import hash_password, login_user
from flask_security import current_user, login_required, roles_required
from app.utils import add_or_update_option, send_notification_mail
from flask import abort, redirect, url_for
from flask_security import roles_required, Security, UserMixin, mail_util
from app.models import User, Role, db, build_sample_db
from flask import Blueprint, render_template, redirect, url_for, request, current_app
import uuid
from flask import jsonify

user_bp = Blueprint('user_bp', __name__)


# Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(datastore=user_datastore)


@user_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """To setup the website on first visit

    Returns:
        _type_: redirect to  login
    """
    # Check if there are existing users in the database
    admin_role = Role.query.filter_by(name="super").first()

    if admin_role:
        admin_users_count = admin_role.users.count()
        if admin_users_count > 0:
            return redirect(url_for('security.login'))

    if request.method == 'POST':
        # Retrieve form data

        password = request.form['password']
        cpassword = request.form['confirmpassword']
        if password != cpassword:
            return render_template('setup.html', msgs=[{
                "msg": "Password Doesn't Match",
                "type": "danger",
            }]), 500

        company = request.form['farmName']
        location = request.form['country']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']

        add_or_update_option("company_name", company)
        add_or_update_option("company_location", location)
        add_or_update_option("company_admin_user", email)

        try:
            # Check if roles already exist before adding
            user_role = Role.query.filter_by(name="user").first()
            if not user_role:
                user_role = Role(name="user")
                db.session.add(user_role)

            admin_role = Role.query.filter_by(name="admin").first()

            if not admin_role:
                admin_role = Role(name="admin")
                db.session.add(admin_role)

            super_role = Role.query.filter_by(name="super").first()
            if not super_role:
                super_role = Role(name="super")
                db.session.add(super_role)
            # print([r.to_dict() for r in [user_role, super_role, admin_role]])
            db.session.commit()
            # Create the initial user if it doesn't already exist
            if not user_datastore.find_user(email=email, case_insensitive=True):
                user = user_datastore.create_user(first_name=first_name,
                                                  last_name=last_name,
                                                  email=email,
                                                  password=hash_password(password), roles=[user_role, super_role, admin_role])

                db.session.commit()
                login_user(user)
                return redirect(url_for('/'))
            # return "Done"
        except Exception as e:
            print(f"An error occurred: {e}")
            return render_template('setup.html', msgs=[{
                "msg": f"An error occurred: {e}",
                "type": "danger",
            }]), 500

    return render_template('setup.html')



@user_bp.route("/user/<email>/<int:id>", methods=['GET', 'DELETE'])
@login_required
@roles_required('admin')
def view_user_information(email: str, id: int):
    """To get the user information

    Args:
        email (str): user email
        id (int): id

    Returns:
        template: html/json
    """
    user = User.query.filter_by(email=email, id=id).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':

        return render_template("user.html", user=user), 200
    elif request.method == 'DELETE':

        # make sure there is atleast 1 admin left after deleting
        admin_role = Role.query.filter_by(name="super").first()
        if admin_role:
            admin_users_count = admin_role.users.count()
            if admin_users_count < 2 and 'super' in user.roles:
                return jsonify({'message': 'Atleast one account should left for an super to operate'}), 404
        # Make sure user doesnt remove themeselves
        if user == current_user:
            return jsonify({'message': 'You are not allowed to remove Your own account'}), 500

        # Check if this is a super user
        roles = user.roles
        # Now you can access the roles associated with the user
        for role in roles:
            if "super" == role.name:
                return jsonify({'message': 'Super users cannot be deleted'}), 500

        # Handle DELETE request (delete user)
        user_datastore.delete_user(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'}), 200



##Add new user in db
@user_bp.route('/api/add_new_user', methods=['POST'])
@login_required
@roles_required('admin')
def add_new_user():
    email = request.form['email']
    password = request.form['password']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    role = Role.query.filter_by(name=request.form['role']).first()

    try:
        invite_user = user_datastore.create_user(
            roles=[role], email=email, first_name=first_name, last_name=last_name, password=password, active=False)
        user_datastore.commit()
        id = invite_user.get_id()
        token = invite_user.get_auth_token()
        domain = current_app.config.get("SYSTEM_DOMAIN")
        msg = f"You have been invited, continue create your account  {domain}/activate/{id}/{token}"
        if not send_notification_mail("Create Accout", msg, [email]):
            user_datastore.delete_user(invite_user)
            user_datastore.commit()
            return "Failed to add new user, email servicee failed", 5000
        flash('Invitation sent successfully!')
        # return redirect(url_for('admin_dashboard'))
        return "Done", 200
    except Exception as e:
        return f"Error {e}", 500


##activate the user, after they click the link in the email
@user_bp.route('/activate/<id>/<token>',methods=['GET'])
def activate_user(id, token):
    try:
        user = user_datastore.find_user(id=id)
        print(user.email)
        if user.verify_auth_token(token):
            user.active = True
            db.session.commit()
            flash('Your account has been activated!', 'success')
            return redirect(url_for('login'))  # Redirect to login page
        else:
            flash('Invalid token or expired token.', 'danger')
            return redirect(url_for('index'))  # Redirect to homepage
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))
    
@user_bp.route('/update_user',methods=['POST'])
@login_required
def update_user():
    data=request.get_json()
    try:
        
      user=User.query.where(User.id==data['id']).first()
      del data["id"]
      user=user.values(**data)
      db.session.execute(user)
      return "Done",200
    except Exception as e:
      print(f'An exception occurred {e}')
      return "Failed to update",500


