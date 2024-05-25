from flask import url_for
from flask_testing import TestCase
from app.app import app,thread_running,mythread,run_pending_schedules,Schedules
from threading import Thread

class TestMyFlaskApp(TestCase):
    """Test class for my flask app"""
    def create_app(self):
        app.config['TESTING'] = True
        
        # mythread = Thread(target=run_pending_schedules)
        # thread_running = True
        # mythread.start()
        return app

    # def test_index_status_code(self):
    #     response = self.client.get('/')
    #     self.assertEqual(response.status_code, 200)
    
    def _post_teardown(self):
        # global thread_running, mythread
        # thread_running = False
        # if mythread and mythread.is_alive():
        #     mythread.join()
        return super()._post_teardown()
    

