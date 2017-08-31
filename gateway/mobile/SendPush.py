import sqlite3 as lite
from pyfcm import FCMNotification

con = lite.connect('fcm_tokens.db')
con.row_factory = lambda cursor, row: row[0]
cur = con.cursor()
cur.execute("SELECT * FROM Tokens")

registration_ids = []
rows = cur.fetchall()
for row in rows:
    registration_ids.append(row)

api_key = "AAAAV-UWVAM:APA91bGnrQ3wkFXQp2aWmFhMCk34MKpT67w1E4CwaJXqtqTQdVBEa_0W5oGqG7-YjWYQQYD5dBhMKqk2Ug8juANPhUHDZyqRGzgna3DL3advPwEF2qJIoFL8-OnHG_wfPGGGuKswGzo-"
push_service = FCMNotification(api_key=api_key)

message_title = "Auto-Tracking-App"
message_body = "Movement was detected"
result = push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)
print (result)

# for registration_id in registration_ids:
#     print (registration_id)
#     result = push_service.notify_single_device(registration_id=registration_id, message_title=message_title, message_body=message_body
#     print (result)
