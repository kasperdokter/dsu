import threading
import inspect

class Application:
    """ An empty concurrent application that can be updated at runtime. """

    def __init__(self):
        self.components = {}
        self.ports = {}

    def add_port(self, name=None):
        uid = name or next(k for k in range(len(self.ports) + 1) if k not in self.ports)
        assert uid not in self.ports, f"Port {uid} already exists."
        p = Port(uid)
        self.ports[uid] = p
        return p

    def add_component(self, name, cls, number_of_inputs, *ports, **params):

        # Instantiate the component
        sourcecode = inspect.getsource(cls)
        uid = f"{name} ({hash(sourcecode)})"
        component = cls(uid, *ports, **params)
        
        # Register the component at the ports
        for source in ports[:number_of_inputs]:
            source.consumer = component
        for target in ports[number_of_inputs:]:
            target.producer = component

        # Register the component at the application
        assert component.uid not in self.components, f"Component {component} already exist."
        self.components[component.uid] = component

        return component

    def update(self, other):

        print("Start updating")

        # Idea rollback stack: in case of error, undo the update

        for component in self.components.values():
            component.upgraded = False
            
        # Create all new ports.
        for port_uid in other.ports:
            if port_uid not in self.ports:
                self.ports[port_uid] = other.ports[port_uid]
                print(f"Port {port_uid} created")
            else:
                other.ports[port_uid].is_upgraded = False

        # Create all new components.
        for component_uid in other.components:
            if component_uid not in self.components:
                self.components[component_uid] = other.components[component_uid]
                print(f"Component {component_uid} created")
        
        # Start the update process
        for obj in self.smother():

            print(f"Smothered {obj}")

            # Terminate or upgrade the component/port
            if isinstance(obj, Port):

                if obj.uid in other.ports: 
                    obj.upgrade(other)
                    print(f"Port {obj} reconnected to {obj.producer} and {obj.consumer}")  
                else:
                    del self.ports[obj.uid]
                    print(f"Port {obj} terminated")

            elif isinstance(obj, Component):

                if obj.uid in other.components:
                    obj.upgraded = True
                    print(f"Component {obj} upgraded")
                else:
                    obj.stop()
                    del self.components[obj.uid]
                    print(f"Component {obj} terminated")

            else:

                raise ValueError(f"Smother must iterate over ports and components, but found {type(obj)}.")

            # Try to start all components, if possible/necessary
            for component in self.components.values():
                if component.startable():
                    print(f"Starting component {component}")
                    component.start()

        for component in self.components.values():
            component.settle()

        print("Completed updating")

    def smother(self):
        raise NotImplementedError()

    def start(self):
        """ Starts all components. """
        for component_uid in self.components:
            self.components[component_uid].start()
    
class Component:

    def __init__(self, uid, *ports, **params):
        self.uid = uid
        self.ports = list(ports)
        self.params = params      
        self.upgraded = True
        self.running = False

    def startable(self):
        return not self.running and all(p.upgraded() for p in self.ports)

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def upgrade(self, app):
        self.upgraded = True

    def settle(self):
        assert self.upgraded, f"Cannot settle {self}"
        self.upgraded = False

    def __repr__(self):
        return self.uid

class ActiveComponent(Component):

    def __init__(self, uid, *ports, **params):
        super().__init__(uid, *ports, **params)
        self.worker = None  

    def run(self):
        raise NotImplementedError()

    def start(self):
        super().start()
        self.worker = threading.Thread(target=self.run, args=self.ports, kwargs=self.params)
        self.worker.name = self.uid
        self.worker.daemon = True
        self.worker.start()

    # def stop(self):
    #     super().stop()
    #     assert self.worker is not None
    #     self.worker.terminate()
    #     self.worker = None

    # def __getstate__(self):
    #     state = self.__dict__.copy()
    #     del state["worker"]
    #     return state

    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     self.worker = None


class Port:
    """ Connects a producer and a consumer. """

    def __init__(self, uid):
        self.uid = uid
        self.producer = None
        self.consumer = None
        self.is_upgraded = True

    def get(self, timeout):
        return self.producer.get(self, timeout)

    def put(self, value):
        self.consumer.put(self, value)    

    def upgraded(self):
        r = self.producer.upgraded and self.consumer.upgraded and self.is_upgraded
        # print(f"port {self} upgraded = {r}")
        return r

    def upgrade(self, app):
        assert self.uid in app.ports
        new_port = app.ports[self.uid]

        def link(component):            
            for i in range(len(component.ports)):
                if component.ports[i].uid == self.uid:
                    component.ports[i] = self

        if self.producer.uid != new_port.producer.uid:
            self.producer = new_port.producer
            link(self.producer)

        if self.consumer.uid != new_port.consumer.uid:
            self.consumer = new_port.consumer
            link(self.consumer)

    def __repr__(self):
        return self.uid
