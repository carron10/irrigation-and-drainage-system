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

SERVER_PORT=5000
SOCK_SERVER_OPTIONS={'ping_interval': 25}
# Flask-Securit y config
SECURITY_URL_PREFIX = "/"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "ATGUOHAELKiubahiughaerGOJAEGj"


# Flask-Security URLs, overridden because they don't put a / at the end

# Flask-Security features
SECURITY_REGISTERABLE =False
SECURITY_SEND_REGISTER_EMAIL = True
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECURITY_RECOVERABLE=True



#Setting security configuration
MAIL_SERVER = 'smtp.example.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'username'
MAIL_PASSWORD = 'password'
