# Module:   node
# Date:     ...
# Author:   ...

"""Node

...
"""

from hashlib import sha256

from .client import Client
from .server import Server

from circuits import handler, BaseComponent


class Node(BaseComponent):
    """Node

    ...
    """

    channel = "node"

    def __init__(self, bind=None, channel=channel):
        super(Node, self).__init__(channel=channel)

        self._bind = bind

        self._nodes = {}

        if self._bind is not None:
            Server(self._bind).register(self)

    def add(self, name, host, port):
        channel = sha256("%s:%d" % (host, port)).hexdigest()
        node = Client(host, port, channel=channel)
        node.register(self)

        self._nodes[name] = node

    @handler("remote")
    def _on_remote(self, e, name, *channels):
        node = self._nodes[name]
        e.channels = channels
        node.send(e)
