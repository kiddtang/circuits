from circuits.web import Controller

from .helpers import urlopen, HTTPError


class Root(Controller):

    def index(self):
        pass


def test(webapp):
    try:
        urlopen(webapp.server.base)
    except HTTPError as e:
        assert e.code == 404
        assert e.msg == "Not Found"
    else:
        assert False
