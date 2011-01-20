from google.appengine.ext import db

#should rename this to Users
class Tokens(db.Model):
    user_id = db.StringProperty()
    email = db.StringProperty()
    pt_username = db.StringProperty()
    pt_email = db.StringProperty()
    pt_token = db.StringProperty()
    signature = db.TextProperty()

class Comments(db.Model):
	token = Tokens()
	projectId = db.StringProperty()
	storyId = db.StringProperty()
	comment = db.TextProperty()
