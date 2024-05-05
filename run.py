from app.app import app
from app.models import db
import logging
monitored_folders = ['app', 'lib']
app.logger.setLevel(logging.ERROR)
if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",use_reloader=False)
