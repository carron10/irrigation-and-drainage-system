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
    if User.query.count() > 0:
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

        # Create roles
        try:
            user_role = Role(name="user")
            super_user_role = Role(name="admin")
            db.session.add(user_role)
            db.session.add(super_user_role)
            db.session.commit()
        except:
            pass
        # Create the initial user
        user = user_datastore.create_user(roles=["admin","user"], first_name=first_name,
                                          last_name=last_name, email=email, password=hash_password(password))
        build_sample_db(user_bp,user_datastore)
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
        # Example: return jsonify({'email': user.email, 'id': user.id})

        # For simplicity, just return a message for demonstration
        return jsonify({'message': 'User information'}), 200
    elif request.method == 'DELETE':
        print(current_user)
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
