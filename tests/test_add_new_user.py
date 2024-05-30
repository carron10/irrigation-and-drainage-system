import unittest
from unittest.mock import patch

from flask import Flask,current_app
from flask_testing import TestCase

from app.app import user_bp, create_app, user_datastore, send_notification_mail
from flask_security import login_user, logout_user

class TestAddNewUser(TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        return app

    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()
        # Simulate admin login for testing (adjust login method if needed)
        login_user(user_datastore.find_user_by_email('admin@example.com'))

    def tearDown(self):
        super().tearDown()
        logout_user()

    @patch('app.app.send_notification_mail')
    def test_add_new_user_success(self, mock_send_notification_mail):
        data = {'email': 'new_user@example.com'}
        response = self.client.post('/api/add_new_user', data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), 'Done')

        # Assert email notification sent (modify based on send_notification_mail implementation)
        mock_send_notification_mail.assert_called_once_with(
            subject="Create Account",
            message=f"You have been invited, continue create your account {current_app.config.get('SYSTEM_DOMAIN')}/comfirn_user/{invite_user.get_auth_token()}",
            recipient_email='new_user@example.com'
        )

    @patch('app.app.user_datastore.create_user')
    def test_add_new_user_error(self, mock_create_user):
        mock_create_user.side_effect = Exception('Error creating user')
        data = {'email': 'invalid_email'}
        response = self.client.post('/api/add_new_user', data=data)

        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Error Exception', response.data)

    # Add more test cases for different scenarios (e.g., invalid email format, unauthorized access)
