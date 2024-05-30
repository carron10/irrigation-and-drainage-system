from flask import url_for
from flask_testing import TestCase
from app.app import app, db
from app.models import Role

class TestSetup(TestCase):
    def create_app(self):
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app

    def setUp(self):
        db.create_all()
        self.test_setup_post_password_mismatch()  # Run password mismatch test first

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_setup_post_password_mismatch(self):
        super_role = Role.query.filter_by(name="super").first()
        if super_role:
            admin_users_count = super_role.users.count()
            self.assertEqual(admin_users_count, 0)
        response = self.client.post(url_for('user_bp.setup'), data={
            'password': 'password',
            'confirmpassword': 'password123',
            'farmName': 'Demo Farm',
            'country': 'South Africa',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': '<EMAIL>',
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn('Password Doesn\'t Match', str(response.data))

    def test_setup_get(self):
        response = self.client.get(url_for('user_bp.setup'))
        self.assert200(response)
        # Add more assertions if needed

    def test_setup_post(self):
        # Assuming the admin role doesn't exist
        super_role = Role.query.filter_by(name="super").first()
        if super_role:
            admin_users_count = super_role.users.count()
            self.assertEqual(admin_users_count, 0)

        data = {
            'password': 'testpassword',
            'confirmpassword': 'testpassword',
            'farmName': 'Test Farm',
            'country': 'Test Country',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com'
        }

        response = self.client.post(
            url_for('user_bp.setup'), data=data, follow_redirects=False)

        # Use _external=True to get the absolute URL for the login route
        expected_location = url_for('security.login', _external=False)
        # Compare the absolute URL of the expected location with the response location
        self.assertEqual(response.location, expected_location)

        # Assert that the admin role is created
        super_role = Role.query.filter_by(name="super").first()
        if super_role:
            admin_users_count = super_role.users.count()
            self.assertEqual(admin_users_count, 1)
        
        # Add more assertions if needed
