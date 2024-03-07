class CommandHandler:
    def __init__(self) -> None:
        self.services={}
    def add_service(self,service_name,service):
        if  self.get_object_type(service).startswith("Unknown"):
            raise Exception("UnkownServiceType")
        self.services[service_name]=service
        
    def get_object_type(self,obj):
        if isinstance(obj,type):
            return "Class"
        elif callable(obj):
            return "Function"
        else:
            if str(obj).find("object at")>0:
                return "ClassObject"
            if str(obj).find("__main__")==1:
                return "ClassObject"
            else:
                return "Unknown type"                
    def process_command(self, command_str):
        command_parts = command_str.split()
        
        service_name = command_parts[0]
        
        command_name = ""
        if len(command_parts)>1:
            command_name = command_parts[1]
            
        
        if service_name in self.services:
            command_handler = self.services[service_name]
            command_args = command_parts[2:]
            if self.get_object_type(command_handler)=="Function":
                command_args = command_parts[1:]
                if not command_name.startswith("-"):
                     return f"Invalid argument: {command_name}"
            if self.get_object_type(command_handler)=="Class":
                if not command_name.startswith("-"):
                    try:
                        command_handler=command_handler()
                    except Exception as e:
                        return f"Exception {e}"
                else:
                    command_args = command_parts[1:]
                
            

            # Parse optional arguments if needed (e.g., --id 123)
            options = {}
            i = 0
            while i < len(command_args):
                args=command_args[i].split("=")
                if args[0].startswith("--"):
                    args[0]=args[0][1:]
                if len(args)>2:
                    return "Argument Parsing Error"
                if len(args)==2:
                    if args[0].startswith("-"):
                        options[args[0][1:]]=args[1]
                    else:
                        return f"Argument Parsing Error {args[0]}"
                else:
                    if args[0].startswith("-"):
                        options[args[0][1:]]=None if not len(command_args)>i+1 else command_args[i+1] if not command_args[i+1].startswith("-") else None
                    else:
                        if i!=0:
                            args=command_args[i-1].split("=")
                            if len(args)==2:
                                return f"Invalid Argument: {command_args[i]}"
                            elif not args[0].startswith("-"):
                                return f"Invalid Argument: {command_args[i]}"
                    
                i=i+1
            
            if self.get_object_type(command_handler)=="Function":
                return command_handler(options)
            
            if command_name.startswith("-"):
                return command_handler(options)
            
            if command_name=="":
                return command_handler
            
            if hasattr(command_handler, command_name):
                if callable(getattr(command_handler, command_name)):
                    return getattr(command_handler, command_name)(options)
                else:
                    return f"Command '{command_name}' is not callable."
            else:
                return f"Unknown command: {command_name}"
        else:
            return f"Unknown service: {service_name}"



# def config(options):
#     return (options)

# class Test1():
#     def start(self,options):
#         return options
# class Test2():
#     def __init__(self) -> None:
#         print("Everything working")

# handler = CommandHandler()
# handler.add_service("config", config)
# handler.add_service("test1", Test1())
# handler.add_service("test2", Test2)

# print(handler.process_command("config --key value -key2 hello  --key3=value3s"))
# print(handler.process_command("test1 start --key value -key2 hello  --key3=value3s"))
# print(handler.process_command("test2"))

