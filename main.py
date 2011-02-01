"""
main module that contains all the url handlers
"""
import os, re, base64
from django.utils import simplejson as json
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.api import users as google_users
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from xml.dom import minidom
from incoming_email import IncomingEmailHandler
from models import Users

from util import StringUtil
from util import ModelsUtil

class MainHandler(webapp.RequestHandler):
	""" handler for / """
	def get(self):
		""" this handler supports http get """
		data = {}
		if google_users.get_current_user():
			google_user = google_users.get_current_user()
			user = db.Query(Users).filter('user_id =', google_user.user_id()).get()

			if user is not None:
				data['token'] = user.pt_token
				data['havetoken'] = user.pt_token is not None

				if user.pt_emails is not None:
					data['emails'] = user.pt_emails

				if len(user.signatures) > 0:
					# convert \n to br so they display correctly
					sigs = []
					count = 0
					for signature in user.signatures:
						sig = {}
						sig['index'] = count
						sig['text'] = StringUtil.nl2br(signature)
						sig['is_html'] = re.search('<.*>', signature) is not None
						sigs.append(sig)
						count = count + 1

					data['signatures'] = sigs

			data['url'] = google_users.create_logout_url(self.request.uri)
			data['user'] = google_users.get_current_user()
		else:
			data['url'] = google_users.create_login_url(self.request.uri)

		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, data))

class GetToken(webapp.RequestHandler):
	"""
	Pulls the user's Pivotal Tracker Token from the API.
	url: /get-token
	"""
	def post(self):
		""" this handler supports http post """

		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is None:
			user = Users(user_id = google_user.user_id(), email = google_user.email())

		username = self.request.get('username')
		password = self.request.get('password')
		token = self.request.get('token')

		if token == '':
			url = 'https://www.pivotaltracker.com/services/v3/tokens/active'
			base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
			authheader =  "Basic %s" % base64string
			result = urlfetch.fetch(url=url,
							headers={"Authorization": authheader})
			if result.status_code == 200:
				token_dom = minidom.parseString(result.content)

				for node in token_dom.getElementsByTagName('token'):
					token = node.getElementsByTagName('guid')[0].firstChild.data
			elif result.status_code == 401:
				self.response.out.write("Invalid Username or Password")
				self.response.set_status(401)
				return
			else:
				self.response.out.write("Error getting token. Please try again later")
				self.response.set_status(400)
				return

		user.pt_username = username
		user.pt_token = token

		db.put(user)

		self.response.out.write(token)

class RemoveToken(webapp.RequestHandler):
	"""
	Removes a Pivotal Tracker token for the user.
	url: /remove-token
	"""
	def post(self):
		""" this handler supports http post """
		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is not None:
			user.delete()
			user = Users(user_id = google_user.user_id(), email = google_user.email())
		else:
			self.response.out.write("Error getting user.")
			self.response.set_status(400)

class SaveEmail(webapp.RequestHandler):
	"""
	Saves a new email for a user. HTTP400 if no email provided or email already exists.
	url: /save-email
	"""
	def post(self):
		""" this handler supports http post """
		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is None:
			user = Users(user_id = google_user.user_id(), email = google_user.email())

		email = self.request.get('email')
		email = email.lower()

		if email == "":
			self.response.set_status(400)
			self.response.out.write('Email is required.')
			return

		try:
			user.pt_emails.index(email)
			self.response.set_status(400)
			self.response.out.write('Email already added')
			return
		except ValueError:
			pass

		user.pt_emails.append(email)
		db.put(user)
		self.response.out.write(json.dumps(user.pt_emails))

class RemoveEmail(webapp.RequestHandler):
	"""
	Removes an email.
	url: /remove-email
	"""
	def post(self):
		""" this handler supports http post """
		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is None:
			user = Users(user_id = google_user.user_id(), email = google_user.email())

		email = self.request.get('email')
		email = email.lower()
		user.pt_emails.remove(email)

		db.put(user)
		self.response.out.write(json.dumps(user.pt_emails))


class SaveSignature(webapp.RequestHandler):
	"""
	Saves a new signature for a user. HTTP400 if the signature already exists.
	Returns all signatures on success.
	url: /save-signature
	"""
	def post(self):
		""" this handler supports http post """
		signature = self.request.get('signature')

		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is None:
			user = Users(user_id = google_user.user_id(), email = google_user.email())

		(code, message) = ModelsUtil.add_signature(user, signature)

		self.response.set_status(code)
		self.response.out.write(message)

class RemoveSignature(webapp.RequestHandler):
	"""
	Removes a signature.
	url: /remove-signature
	"""
	def post(self):
		""" this handler supports http post """
		google_user = google_users.get_current_user()
		user = db.Query(Users).filter('user_id =', google_user.user_id()).get()
		if user is None:
			user = Users(user_id = google_user.user_id(), email = google_user.email())

		index = self.request.get('signature')
		user.signatures.pop(int(index))
		db.put(user)

		sigs = []
		for signature in user.signatures:
			sigs.append(StringUtil.nl2br(signature))

		self.response.out.write(json.dumps(sigs))

class UpdateSchema(webapp.RequestHandler):
	"""
	Ensures that the schema of DataStore elements has all the necessary fields.
	url: /update-schema
	"""
	def get(self):
		""" this handler supports http get """

def main():
	""" Sets up the url handler mapping. """
	application = webapp.WSGIApplication([('/', MainHandler),
										  ('/get-token', GetToken),
										  ('/remove-token', RemoveToken),
										  ('/save-email', SaveEmail),
										  ('/remove-email', RemoveEmail),
										  ('/save-signature', SaveSignature),
										  ('/remove-signature', RemoveSignature),
										  ('/update-schema', UpdateSchema),
										  IncomingEmailHandler.mapping()
										 ],
										 debug=True)
	util.run_wsgi_app(application)

if __name__ == '__main__':
	main()
