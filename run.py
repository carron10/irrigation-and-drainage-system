import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread, Event
from app.app import app, run_pending_schedules, scheduler
from app.models import db
import logging

stop_event = Event()
# def restart_thread():
#     global mythread
#     if mythread.is_alive():
#         logging.info("Stopping existing thread...")
#         stop_event.set()
#         mythread.join()  # Wait for the thread to finish
    


# # Define a callback function
# def on_file_change(event):
#     # print(f"File {event.src_path} has been modified! Triggering callback function.")
#     restart_thread()
#     # Add your custom callback logic here
# # Create an event handler
# class MyEventHandler(FileSystemEventHandler):
#     def on_modified(self, event):
#         on_file_change(event)

def run_pending():
    run_pending_schedules()
    while not stop_event.is_set():
        scheduler.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # Define the path to the Flask application files

    mythread = Thread(target=run_pending, daemon=True)
    mythread.start()
    
    # Start the Flask application
    app.run(debug=True, host="0.0.0.0", port=5000,use_reloader=False)

    stop_event.set()
