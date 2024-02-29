
# Create Flask instance

from flask import Flask

def create_app():
    app = Flask(__name__,static_url_path='',static_folder='static',template_folder='templates')
    #Configuration
    app.config.from_pyfile('config.py')
    return app