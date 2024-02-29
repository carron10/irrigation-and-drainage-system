
from flask_sock import Sock
import json 

class WebSocket(Sock):
    """Instantiate the Websocket Class extension.

    :param app: The Flask application instance. 
    :param route: The route for websocket, if not provided '/' will be used
    """
    def __init__(self, app=None,route='/'):
        super().__init__(app)
        self.events={'connect':[]}
        @self.route(route)
        def echo(ws):
            for func in self.events["connect"]:
                    func({},ws)
            while True:
                data=ws.receive()
                data = json.loads(data)
                event=data['event']
                for func in self.events[event]:
                    func(data['data'],ws)
                
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



