# Module:   core
# Date:     2nd April 2006
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""
Core of the circuits library containing all of the essentials for a
circuits based application or system. Normal usage of circuits:

>>> from circuits import listener, Manager, Component, Event
"""

import new
from itertools import chain
from threading import Thread
from functools import partial
from collections import deque
from collections import defaultdict
from sys import exc_info as _exc_info
from sys import exc_clear as _exc_clear
from inspect import getargspec, getmembers


class InvalidHandler(Exception):
    """Invalid Handler Exception

    Invalid Handler Exception raised when adding a callable
    to a manager that was not decorated with the
    :func:`listener decorator <circuits.core.listener>`.
    """

    def __init__(self, handler):
        "initializes x; see x.__class__.__doc__ for signature"

        super(InvalidHandler, self).__init__()

        self.handler = handler


class Event(object):
    """Create a new Event Object

    Create a new event object populating it with the given
    list of arguments and keyword arguments.

    :param args: list of arguments for this event
    :type args: list/tuple or iterable
    :param kwargs: keyword arguments for this event
    :type kwargs: dict
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        self.name = self.__class__.__name__
        self.channel = None
        self.target = None

        self.source = None  # Used by Bridge
        self.ignore = False # Used by Bridge

    def __eq__(self, y):
        """ x.__eq__(y) <==> x==y

        Tests the equality of event self against event y.
        Two events are considered "equal" iif the name,
        channel and target are identical as well as their
        args and kwargs passed.
        """

        attrs = ("name", "args", "kwargs", "channel", "target")
        return all([getattr(self, a) == getattr(y, a) for a in attrs])

    def __repr__(self):
        "x.__repr__() <==> repr(x)"

        if self.channel is not None and self.target is not None:
            channelStr = "%s:%s" % (self.target, self.channel)
        elif self.channel is not None:
            channelStr = self.channel
        else:
            channelStr = ""
        argsStr = ", ".join([("%s" % repr(arg)) for arg in self.args])
        kwargsStr = ", ".join(
                [("%s=%s" % kwarg) for kwarg in self.kwargs.iteritems()])
        return "<%s[%s] (%s, %s)>" % (self.name, channelStr, argsStr, kwargsStr)

    def __getitem__(self, x):
        """x.__getitem__(y) <==> x[y]

        Get and return data from the event object requested by "x".
        If an int is passed to x, the requested argument from self.args
        is returned index by x. If a str is passed to x, the requested
        keyword argument from self.kwargs is returned keyed by x.
        Otherwise a TypeError is raised as nothing else is valid.
        """

        if type(x) == int:
            return self.args[x]
        elif type(x) == str:
            return self.kwargs[x]
        else:
            raise TypeError("Expected int or str, got %r" % type(x))


class Error(Event):
    """Error(type, value, traceback) -> Error Event

    type:      Exception type      -> sys.exc_type
    value:     Exception value     -> sys.exc_value
    traceback: Exception traceback -> sys.exc_traceback
    """

def listener(*args, **kwargs):
    """Creates an Event Handler of a callable object

    Decorator to wrap a callable into an event handler that
    listens on a set of channels defined by args. The type
    of the listener defaults to "listener" and is defined
    by kwargs["type"]. To define a filter, pass type="filter"
    to kwargs. If kwargs["target"] is not None, this event handler
    will be registered and will ignore the channel of it's containing
    Component.
    
    Examples:

    >>> from circuits.core import listener
    >>> @listener("foo")
    ... def onFOO():
    ...     pass
    >>> @listener("bar", type="filter")
    ... def onBAR():
    ...     pass
    >>> @listener("foo", "bar")
    ... def onFOOBAR():
    ...     pass
    """

    def decorate(f):
        f.type = kwargs.get("type", "listener")
        f.target = kwargs.get("target", None)
        f.channels = args

        _argspec = getargspec(f)
        _args = _argspec[0]
        if _args and _args[0] == "self":
            del _args[0]
        if _args and _args[0] == "event":
            f._passEvent = True
        else:
            f._passEvent = False

        return f
    return decorate


class HandlersType(type):

    def __init__(cls, name, bases, dct):
        super(HandlersType, cls).__init__(name, bases, dct)

        for k, v in dct.iteritems():
            if callable(v) and not (k[0] == "_" or hasattr(v, "type")):
                setattr(cls, k, listener(k, type="listener")(v))


class Manager(object):
    """Creates a new Manager

    Create a new event manager which manages Components and Events.
    """

    def __init__(self, *args, **kwargs):
        "initializes x; see x.__class__.__doc__ for signature"

        super(Manager, self).__init__()

        self._queue = deque()
        self._handlers = set()
        self._components = set()
        self._channels = defaultdict(list)

        self.manager = self

    def __repr__(self):
        q = len(self._queue)
        h = len(self._handlers)
        return "<Manager (q: %d h: %d)>" % (q, h)

    def __len__(self):
        return len(self._queue)

    def __add__(self, y):
        y.register(self.manager)
        if hasattr(y, "registered"):
            y.registered()
        return self
    
    def __iadd__(self, y):
        y.register(self.manager)
        if hasattr(y, "registered"):
            y.registered()
        return self

    def __sub__(self, y):
        if y.manager == self:
            y.unregister()
            if hasattr(y, "unregistered"):
                y.unregistered()
            return self
        else:
            raise TypeError("No registration found for %r" % y)

    def __isub__(self, y):
        if y.manager == self:
            y.unregister()
            if hasattr(y, "unregistered"):
                y.unregistered()
            return self
        else:
            raise TypeError("No registration found for %r" % y)

    def handlers(self, s):
        if s == "*:*":
            return self._handlers

        if ":" in s:
            target, channel = s.split(":", 1)
        else:
            channel = s
            target = None

        channels = self.channels
        globals = channels["*"]

        if target == "*":
            c = ":%s" % channel
            x = [channels[k] for k in channels if k == channel or k.endswith(c)]
            all = [i for y in x for i in y]
            return chain(globals, all)

        if channel == "*":
            c = "%s:" % target
            x = [channels[k] for k in channels if k.startswith(c) or ":" not in k]
            all = [i for y in x for i in y]
            return chain(globals, all)

        handlers = globals
        if channel in channels:
            handlers = chain(handlers, channels[channel])
        if target and "%s:*" % target in channels:
            handlers = chain(handlers, channels["%s:*" % target])
        if "*:%s" % channel in channels:
            handlers = chain(handlers, channels["*:%s" % channel])
        if target:
            handlers = chain(handlers, channels[s])

        return handlers

    @property
    def components(self):
        return self._components.copy()

    @property
    def channels(self):
        return self._channels

    def _add(self, handler, channel=None):
        """E._add(handler, channel) -> None

        Add a new filter or listener to the event manager
        adding it to the given channel. If no channel is
        given, add it to the global channel.
        """

        if getattr(handler, "type", None) not in ["filter", "listener"]:
            raise InvalidHandler(handler)

        self._handlers.add(handler)

        if channel is None:
            channel = "*"

        if channel in self.channels:
            if handler not in self.channels[channel]:
                self._channels[channel].append(handler)
                self._channels[channel].sort(key=lambda x: x.type)
        else:
            self._channels[channel] = [handler]

    def _remove(self, handler, channel=None):
        """E._remove(handler, channel=None) -> None

        Remove the given filter or listener from the
        event manager removing it from the given channel.
        if channel is None, remove it from the global
        channel. This will succeed even if the specified
        handler has already been removed.
        """

        if channel is None:
            if handler in self.channels["*"]:
                self._channels["*"].remove(handler)
            keys = self.channels.keys()
        else:
            keys = [channel]

        if handler in self._handlers:
            self._handlers.remove(handler)

        for channel in keys:
            if handler in self.channels[channel]:
                self._channels[channel].remove(handler)


    def push(self, event, channel, target=None):
        """E.push(event, channel, target=None) -> None

        Push the given event onto the given channel.
        This will queue the event up to be processed later
        by flushEvents. If target is given, the event will
        be queued for processing by the component given by
        target.
        """

        if self.manager == self:
            self._queue.append((event, channel, target))
        else:
            self.manager.push(event, channel, target)

    def flush(self):
        """E.flushEvents() -> None

        Flush all events waiting in the queue.
        Any event waiting in the queue will be sent out
        to filters/listeners.
        """

        if self.manager == self:
            q = self._queue
            self._queue = deque()
            while q:
                event, channel, target = q.pop()
                self.send(event, channel, target)
        else:
            self.manager.flush()

    def send(self, event, channel, target=None, errors=False, log=True):
        """E.send(event, channel, target=None, errors=False) -> None

        Send the given event to filters/listeners on the
        channel specified. If target is given, send this
        event to filters/listeners of the given target
        component.
        """

        if self.manager == self:
            event.channel = channel
            event.target = target
            eargs = event.args
            ekwargs = event.kwargs
            if target is not None:
                channel = "%s:%s" % (target, channel)

            r = False
            for handler in self.handlers(channel):
                try:
                    if handler._passEvent:
                        r = partial(handler, event, *eargs, **ekwargs)()
                    else:
                        r = partial(handler, *eargs, **ekwargs)()
                except:
                    if log:
                        self.push(Error(*_exc_info()), "error")
                    if errors:
                        raise
                    else:
                        _exc_clear()

                if r is not None and r and handler.type == "filter":
                    break
            return r
        else:
            return self.manager.send(event, channel, target, errors, log)

    def start(self):
        self.thread = Thread(None, self._run, self.__class__.__name__)
        self.running = True
        self.thread.setDaemon(True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def _calls(self):
        for v in vars(self).itervalues():
            if isinstance(v, Manager):
                yield v.__tick__

    def _run(self):
        while self.running and self.thread.isAlive():
            [f() for f in self._calls()]
            self.manager.flush()

    def run(self):
        while True:
            try:
                [f() for f in self._calls()]
                self.manager.flush()
            except (KeyboardInterrupt, SystemExit):
                break

class BaseComponent(Manager):
    """Creates a new Component

    Subclasses of Component define Event Handlers by decorating
    methods by using the listener decorator.

    All listeners found in the Component will automatically be
    picked up when the Component is instantiated.

    :param channel: channel this Component listens on (*default*: ``None``)
    :type channel: str
    """

    channel = None

    def __init__(self, *args, **kwargs):
        "initializes x; see x.__class__.__doc__ for signature"

        super(BaseComponent, self).__init__(*args, **kwargs)

        self.channel = kwargs.get("channel", self.channel)
        self.register(self)


    def __repr__(self):
        name = self.__class__.__name__
        channel = self.channel or ""
        q = len(self._queue)
        h = len(self._handlers)
        return "<%s/%s component (q: %d h: %d)>" % (name, channel, q, h)

    def register(self, manager):
        p = lambda x: callable(x) and hasattr(x, "type")
        handlers = [v for k, v in getmembers(self, p)]

        for handler in handlers:
            if handler.channels:
                channels = handler.channels
            else:
                channels = ["*"]

            for channel in channels:
                if self.channel is not None:
                    if handler.target is not None:
                        target = handler.target
                    else:
                        target = self.channel

                    channel = "%s:%s" % (target, channel)

                manager._add(handler, channel)

        self.manager = manager
        self.manager._components.add(self)


    def unregister(self):
        "Unregister all registered event handlers from the manager."

        for handler in self._handlers.copy():
            self.manager._remove(handler)

        if self in self.manager.components:
            self.manager._components.remove(self)

        self.manager = self

class Component(BaseComponent):

    __metaclass__ = HandlersType

    def __new__(cls, *args, **kwargs):
        self = BaseComponent.__new__(cls, *args, **kwargs)
        for base in cls.__bases__:
            if issubclass(cls, base):
                for k, v in base.__dict__.iteritems():
                    if callable(v) and hasattr(v, "type"):
                        name = "%s_%s" % (base.__name__, k)
                        method = new.instancemethod(v, self, cls)
                        setattr(self, name, method)
        return self
