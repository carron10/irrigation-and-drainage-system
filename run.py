from app.app import app
from app.models import db
monitored_folders = ['app', 'lib']

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",extra_files=monitored_folders)
