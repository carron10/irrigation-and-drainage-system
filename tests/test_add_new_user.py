# import unittest
# from app.app import app, user_bp
# from unittest.mock import patch, Mock

# class TestUserRoutes(unittest.TestCase):
#     def setUp(self):
#         self.app = app.test_client()
#         self.app.testing = True
#         self.app.config['TESTING'] = True
#     def test_setup_get(self):
#         response = self.app.get('/setup')
#         self.assertEqual(response.status_code, 200)
#         self.assertIn('Setup form', str(response.data))

#     def test_setup_post_password_mismatch(self):
#         with self.app.test_request_context():
#             with patch('app.user_routes.add_or_update_option', side_effect=Mock()):
#                 response = self.app.post('/setup', data={
#                     'password': 'password',
#                     'confirmpassword': 'password123',
#                     'farmName': 'Demo Farm',
#                     'country': 'South Africa',
#                     'first_name': 'John',
#                     'last_name': 'Doe',
#                     'email': '<EMAIL>',
#                 })
#                 self.assertEqual(response.status_code, 500)
#                 self.assertIn('Password Doesn\'t Match', str(response.data))

#     @patch('app.user_routes.user_datastore.find_user')
#     @patch('app.user_routes.user_datastore.create_user')
#     def test_setup_post_success(self, mock_create_user, mock_find_user):
#         mock_find_user.return_value = None
#         with self.app.test_request_context():
#             with patch('app.user_routes.add_or_update_option', side_effect=Mock()):
#                 response = self.app.post('/setup', data={
#                     'password': 'password',
#                     'confirmpassword': 'password',
#                     'farmName': 'Demo Farm',
#                     'country': 'South Africa',
#                     'first_name': 'John',
#                     'last_name': 'Doe',
#                     'email': '<EMAIL>',
#                 })
                
#                 self.assertEqual(response.status_code, 302)
#                 self.assertRedirects(response, location='http://localhost/login')
#                 mock_find_user.assert_called_with(email='<EMAIL>', case_insensitive=True)
#                 mock_create_user.assert_called_with(first_name='John', last_name='Doe', email='<EMAIL>', password=hash_password('password'), roles=[Mock(), Mock(), Mock()])

# if __name__ == '__main__':
#     unittest.main()
