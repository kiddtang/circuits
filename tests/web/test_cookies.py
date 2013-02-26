#!/usr/bin/env python

from circuits.web import Controller

from .helpers import build_opener, HTTPCookieProcessor
from .helpers import CookieJar


class Root(Controller):
    def index(self):
        visited = self.cookie.get("visited")
        if visited and visited.value:
            return "Hello again!"
        else:
            self.cookie["visited"] = True
            return "Hello World!"


def test(webapp):
    cj = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cj))

    f = opener.open(webapp.server.base)
    s = f.read()
    assert s == b"Hello World!"

    f = opener.open(webapp.server.base)
    s = f.read()
    assert s == b"Hello again!"
