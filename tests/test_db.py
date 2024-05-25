from flask import url_for
from flask_testing import TestCase
from app.app import app,thread_running,mythread,run_pending_schedules,Schedules
from threading import Thread

class TestMyFlaskApp(TestCase):
    """Test class for my flask app"""
    def create_app(self):
        app.config['TESTING'] = True
    
        return app


    def test_schedules(self):
        schedules = Schedules.query.filter_by(status=False).all()
    def _post_teardown(self):
        global thread_running, mythread
        thread_running = False
        if mythread and mythread.is_alive():
            mythread.join()
        return super()._post_teardown()
    

