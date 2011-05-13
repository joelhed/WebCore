"""A basic hello world application.

This can be simplified down to 5 lines in total; two import lines, two
controller lines, and one line to serve it.
"""
import logging

from paste import httpserver

from web.core import Application
from web.rpc.amf import AMFController


class TestService(AMFController):
    def hello(self, name="world"):
        return "Hello, %(name)s!" % dict(name=name)


class RootController(AMFController):
    test = TestService()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = Application.factory(root=RootController, debug=False)
    httpserver.serve(app, host='127.0.0.1', port='8080')
