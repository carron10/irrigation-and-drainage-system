import os
import selectors

# Create dummy secrey key
SECRET_KEY = '123456790'


# Create in-memory database
DATABASE_FILE = 'sample_db.sqlite'

#or use postgress[for online app instance]
SQLALCHEMY_DATABASE_URI = os.environ.get("POSTGRES_URL")
if SQLALCHEMY_DATABASE_URI==None:
    SQLALCHEMY_DATABASE_URI="sqlite:///"+DATABASE_FILE
    

SQLALCHEMY_ECHO = False

SERVER_PORT=5000
SOCK_SERVER_OPTIONS={'ping_interval': 25}


# Flask-Security config
SECURITY_URL_PREFIX = "/"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "ATGUOHAELKiubahiughaerGOJAEGj"


# Flask-Security features
SECURITY_REGISTERABLE =False
SECURITY_SEND_REGISTER_EMAIL = True
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECURITY_RECOVERABLE=True


DEBUG = False
TESTING = False

# Flask-Mail configurations
MAIL_SERVER = 'mail.tekon.co.zw'
MAIL_HOST=MAIL_SERVER
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'noreply@tekon.co.zw'
MAIL_PASSWORD = 'unAHqC3fLqGeF4X'
MAIL_DEFAULT_SENDER="noreply@tekon.co.zw"

#Configure the domain name
SYSTEM_DOMAIN="https://irrigation-and-drainage-system.onrender.com/"