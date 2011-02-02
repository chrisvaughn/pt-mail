""" models module contains the App Engine DataStore models """
from google.appengine.ext import db

class Users(db.Model):
    user_id = db.StringProperty()
    email = db.StringProperty()
    pt_username = db.StringProperty()
    pt_emails = db.StringListProperty()
    pt_token = db.StringProperty()
    signatures = db.ListProperty(db.Text)

class Comments(db.Model):
    user_id = db.StringProperty()
    project_id = db.StringProperty()
    story_id = db.StringProperty()
    comment = db.TextProperty()
