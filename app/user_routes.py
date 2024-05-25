from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required
)
from flask_security.utils import hash_password, login_user
from flask_security import current_user, login_required, roles_required
from app.utils import add_or_update_option
from flask import abort, redirect, url_for
from flask_security import roles_required, Security, UserMixin, mail_util
from app.models import User, Role, db, build_sample_db
from flask import Blueprint, render_template, redirect, url_for, request
import uuid
from flask import jsonify

user_bp = Blueprint('user_bp', __name__)


# Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(datastore=user_datastore)


@user_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    # Check if there are existing users in the database
    admin_role = Role.query.filter_by(name="admin").first()
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

            db.session.commit()
            # Create the initial user if it doesn't already exist
            if not user_datastore.find_user(email=email):
                user = user_datastore.create_user(roles=[user_role, super_role, admin_role],
                                                  first_name=first_name,
                                                  last_name=last_name,
                                                  email=email,
                                                  password=hash_password(password))
            db.session.commit()

        except Exception as e:
            print(f"An error occurred: {e}")

        build_sample_db(user_bp, user_datastore)
        db.session.commit()
        return redirect(url_for('security.login'))

    return render_template('setup.html')


# Redirect regular users attempting to access the registration page
# @user_bp.route('/register', methods=['GET', 'POST'])
# def register():
#     return redirect('/')  # Redirect to another page


@user_bp.route("/user/<email>/<int:id>", methods=['GET', 'DELETE'])
@login_required
@roles_required('admin')
def view_user_information(email: str, id: int):
    user = User.query.filter_by(email=email, id=id).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        # Handle GET request (view user information)
        # return jsonify({'email': user.email, 'id': user.id})

        # For simplicity, just return a message for demonstration
        return jsonify({'message': 'User information'}), 200
    elif request.method == 'DELETE':

        # make sure there is atleast 1 admin left after deleting
        admin_role = Role.query.filter_by(name="admin").first()
        if admin_role:
            admin_users_count = admin_role.users.count()
            if admin_users_count > 1:
                return jsonify({'message': 'Atleast one account should left for an admin to operate'}), 404
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


@user_bp.route('/api/add_new_user', methods=['POST'])
@login_required
@roles_required('admin')
def add_new_user():
    email = request.form['email']
    invite_user = user_datastore.create_user(email=email, active=False)
    try:
        user_datastore.commit()
        token = user_datastore.get_confirmation_token(invite_user)
        send_invitation_email(invite_user, token)
        flash('Invitation sent successfully!')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        user_datastore.rollback()
        flash(f'Error inviting user: {str(e)}')
        return redirect(url_for('invite_user'))
