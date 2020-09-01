import dsu
# import multiprocessing
import queue
import time
import random
import traceback

class Producer(dsu.ActiveComponent):

    def run(self, target):
        print(f"{self} started")
        try:
            while self.running:
                target.put(random.randint(0,999))
        except:
            with open('producer.log', 'w') as f:
                f.writelines(traceback.format_exc())
        print(f"{self} terminated")

class Consumer(dsu.ActiveComponent):

    def run(self, source):
        print(f"{self} started")
        try:
            while self.running:
                value = source.get(timeout=2.0)
                if value is None:
                    continue
                print(value)
                time.sleep(1)
        except:
            with open('consumer.log', 'w') as f:
                f.writelines(traceback.format_exc())
        print(f"{self} terminated")

class Buffer(dsu.Component):

    def __init__(self, name, source, target, maxsize=10):
        super().__init__(name, source, target)
        # self.items = multiprocessing.Queue(maxsize)
        self.items = queue.Queue(maxsize)

    def put(self, port, value):
        assert port == self.ports[0], f"Put must be at input"
        self.items.put(value)

    def get(self, port, timeout=None):
        assert port == self.ports[1], f"Get must be at output"
        return self.items.get(timeout=timeout)


class Main(dsu.Application):

    def __init__(self):
        super().__init__()
        
        self.a = self.add_port('a')
        self.b = self.add_port('b')

        self.producer = self.add_component('producer', Producer, 0, self.a)
        self.buffer = self.add_component('buffer', Buffer, 1, self.a, self.b)
        self.consumer = self.add_component('consumer', Consumer, 1, self.b)

    def smother(self):
        """ GENERATED CODE from automata specs with quiescence. """
        yield self.producer
        yield self.a
        while self.buffer.items.qsize() > 0:
            time.sleep(1)
            print(f"waiting for {self.buffer} to drain (size={self.buffer.items.qsize()})")
        yield self.buffer
        yield self.b
        yield self.consumer

    