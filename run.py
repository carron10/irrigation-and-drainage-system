from app.app import app
from app.models import db

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0")
