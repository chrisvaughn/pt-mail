from google.appengine.ext import db

class Tokens(db.Model):
    user_id = db.StringProperty()
    email = db.StringProperty()
    pt_username = db.StringProperty()
    pt_email = db.StringProperty()
    pt_token = db.StringProperty()

