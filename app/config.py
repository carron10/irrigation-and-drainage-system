import os
import selectors
# Create dummy secrey key so we can use sessions
SECRET_KEY = '123456790'
# Create in-memory database
DATABASE_FILE = 'sample_db.sqlite'
SQLALCHEMY_DATABASE_URI = os.environ.get("POSTGRES_URL")
if SQLALCHEMY_DATABASE_URI==None:
    SQLALCHEMY_DATABASE_URI="sqlite:///"+DATABASE_FILE
SQLALCHEMY_ECHO = False

        
SOCK_SERVER_OPTIONS={'ping_interval': 25}
# Flask-Securit y config
SECURITY_URL_PREFIX = "/"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "ATGUOHAELKiubahiughaerGOJAEGj"

# Flask-Security URLs, overridden because they don't put a / at the end
# SECURITY_LOGIN_URL = "/login/"
# SECURITY_LOGOUT_URL = "/logout/"
# SECURITY_REGISTER_URL = "/register/"

# SECURITY_POST_LOGIN_VIEW = "/admin/"
# SECURITY_POST_LOGOUT_VIEW = "/admin/"
# SECURITY_POST_REGISTER_VIEW = "/admin/"

# Flask-Security features
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECURITY_RECOVERABLE=True
