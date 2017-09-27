import logging
import sqlite3

from pyfcm import FCMNotification


def insert_token(token):
    try:
        con = sqlite3.connect('fcm.db')
        cur = con.cursor()

        cur.execute('CREATE TABLE IF NOT EXISTS tokens(token TEXT)')
        cur.execute('INSERT INTO tokens VALUES (?)', (token, ))

        con.commit()
    finally:
        if cur:
            cur.close()
        if con:
            con.close()


def notify_all(message_title=None, message_body=None):
    con = sqlite3.connect('fcm.db')
    con.row_factory = lambda cursor, row: row[0]

    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS tokens(token TEXT)')
    cur.execute('SELECT * FROM tokens')

    registration_ids = [row for row in cur.fetchall()]
    if len(registration_ids) > 0:
        noti = FCMNotification('API-KEY')
        result = noti.notify_multiple_devices(registration_ids=registration_ids,
                                              message_title=message_title,
                                              message_body=message_body)

        return result
