from flask import url_for
from flask_testing import TestCase
from app.app import app, thread_running, mythread,run_pending_schedules, Schedules, user_datastore, send_notification_mail
from threading import Thread
import unittest
from unittest.mock import ANY,patch
from flask_security import current_user
from app.models import User  # Import your User model

class TestMyFlaskApp(TestCase):
    """Test class for my flask app"""

    def create_app(self):
        global thread_running, mythread
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        mythread = Thread(target=run_pending_schedules)
        thread_running = True
        mythread.start()
        return app

    def _post_teardown(self):
        global thread_running, mythread
        thread_running = False
        if mythread and mythread.is_alive():
            mythread.join()
        return super()._post_teardown()
