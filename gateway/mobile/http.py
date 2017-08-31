import logging
import threading
import json
import re
import sqlite3 as lite

from tornado.httpserver import HTTPServer
from tornado.web import Application, RequestHandler

logger = logging.getLogger(__name__)


class CameraRequestHandler(RequestHandler):
    # TODO: Handle camera requests
    pass


class MoveRequestHandler(RequestHandler):
    def post(self):
        # TODO: Move camera
        pass


class ModeRequestHandler(RequestHandler):
    def post(self):
        # TODO: Select mode
        pass

class TokenRequestHandler(RequestHandler):
    def post(self):
        # TODO: insert token to db
        json_data = self.request.body.decode("utf-8")
        data = json.loads(json_data)
        # print ('recieved data:', data)

        if "token" in data:
            token = data['token']
            print ('received token:', token)

            con = lite.connect('fcm_tokens.db')
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS Tokens(token TEXT)")
            cur.execute("INSERT INTO Tokens VALUES (?)", (token, ))
            cur.execute("SELECT * FROM Tokens")

            # rows = cur.fetchall()
            # for row in rows:
            #     print (row)

            con.commit()
            cur.close()
            con.close()
        pass

def get_application():
    return Application([
        (r'/camera', CameraRequestHandler),
        (r'/move', MoveRequestHandler),
        (r'/mode', ModeRequestHandler),
        (r'/token', TokenRequestHandler),
    ])
