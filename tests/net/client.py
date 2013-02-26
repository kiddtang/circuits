from circuits import Component


class Client(Component):

    channel = "client"

    def __init__(self, channel=channel):
        super(Client, self).__init__(channel=channel)

        self.data = ""
        self.ready = False
        self.closed = False
        self.connected = False
        self.disconnected = False

    def ready(self, *args):
        self.ready = True

    def connected(self, host, port):
        self.connected = True

    def disconnected(self):
        self.disconnected = True

    def closed(self):
        self.closed = True

    def read(self, *args):
        if len(args) == 2:
            _, data = args
        else:
            data = args[0]

        self.data = data
