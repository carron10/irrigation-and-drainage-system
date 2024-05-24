from app.app import app,thread_running,mythread,run_pending_schedules
from threading import Thread
from app.models import db
import logging
if __name__ == "__main__":
    # Start scheduler on new Thread
    mythread = Thread(target=run_pending_schedules)
    thread_running = True
    mythread.start()
    app.run(debug=True,host="0.0.0.0",port=5000)
