
from app.websocket.flask_sock import Sock
import json 
import time

class WebSocket(Sock):
    """Instantiate the Websocket Class extension.
    This classs  extends the Sock class-- it allows one to use one route for communication, and added events such that client communicate with server using events..
    :param app: The Flask application instance. 
    :param route: The route for websocket, if not provided '/' will be used
    """

    def init_app(self, app):
        '''If app instance is not provided when creating this object, one should use this function to add it...'''
        return super().init_app(app)
    
    def __init__(self, app=None,route='/',require_events=True):
        super().__init__(app)
        self.events={'connect':[],'disconnect':[]}
        def on_disconnect(*args, **kwargs):
            for func in self.events["disconnect"]:
                    func(*args, **kwargs)

        @self.route(route,on_disconnect=on_disconnect)
        def echo(ws,*args, **kwargs):
            for func in self.events["connect"]:
                    func(ws,*args, **kwargs)
            while True:
                    data=ws.receive()
                    data = json.loads(data)
                    # print("recevied",data)
                    event=data['event']
                    if event in self.events:
                        for func in self.events[event]:
                            func(data['data'],ws,*args, **kwargs)
                
          
    def on(self,event:str):
        """The decorator to listen to events:
        The decorated function will be invoked when an event happen ...defined from the client, with data(from the client) and a WebSocket connect object passed
        as an argument. Example
            @websock.on('connect')
            def websocket_route(data,ws):
                # The ws object has the following methods:
                # - ws.send(data)
                # - ws.receive(timeout=None)
                # - ws.close(reason=None, message=None)
        :param event: The event to listen to e.g connect event,my_event and etc
        """
        def inner(func):
            if event in self.events:
                self.events[event].append(func)
            else:
              self.events[event]=[func]
        return inner
    def on_temp_event(self,event:str):
        '''Because websocket are different from http, the data is sent in an unorderd manner, which means if the server send data to client, 
         if the client need to return a response to the data sent, the response can reach the server late or after receiving other different data, to solve this 
         we can tell the client to send the reponse to a specific url or send the response back with some referal(indicating that this is a reponse to which message...)
         Because the client and sever communicates using event, the server can send a message to the client,specifying an event that the client to should fireback 
         to that event.....
        '''
        return self.on(event=event)
    def remove_event(self,event: str):
        '''To remove an event: Its advisable to remove temporal events after they have been exectued...'''
        if event in self.events:
            del self.events[event]
            



