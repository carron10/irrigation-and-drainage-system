# test_mail.py

import unittest
from app.app import app, mail
from app.utils import send_notification_mail
class TestMail(unittest.TestCase):
    def setUp(self):
        app.config.from_pyfile('config.py')
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_send_email(self):
       with app.app_context():
        response = send_notification_mail("Test Email","Testing an email",['admin@tekon.co.zw',"carronmuleya10@gmail.com"])
        self.assertEqual(response, True)

if __name__ == '__main__':
    unittest.main()
