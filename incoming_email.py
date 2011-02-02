"""
incoming_email module handles any email delivered to the app engine site.
"""
import logging, re
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import urlfetch
from xml.dom import minidom
from google.appengine.ext import db
from models import Users
from models import Comments
from google.appengine.api import mail

from util import ModelsUtil
from util import StringUtil
from util import PTUtil

# use Beautiful Soup to strip html (or parse it later if we want)
from BeautifulSoup import BeautifulSoup

class IncomingEmailHandler(InboundMailHandler):
	""" Handles all incoming email. """

	noreply = "PT Reply <no-reply@ptreply.com>"
	error_subject = "PT Reply Error"
	error_recipients = ('kevin.morey@gmail.com', 'chrisvaughn01@gmail.com')

	email_pattern = re.compile('(([-a-z0-9_.+]+)@([-a-z0-9]+\.)+[a-z]{2,6})', re.IGNORECASE)

	def receive(self, message):
		""" Called when an email is received. """
		match = self.email_pattern.search(message.to)
		if match is None:
			logging.error("couldn't find which handler to use")
			return

		addressed_to = match.group(2).lower()
		logging.info("Received a message addressed to: %s", addressed_to)

		if addressed_to == 'signature' or addressed_to == 'sig':
			self.handle_signature(message)
		else:
			self.handle_comment(message)

	def parse_message(self, message):
		""" Parse the email and return sender, message_body, and is_html. """
		match = self.email_pattern.search(message.sender)
		if match is not None:
			sender = match.group(1)
		else:
			logging.error("couldn't find sender")
			return

		sender = sender.lower()
		logging.info("Received a message from: %s", sender)

		#if subject is blank the attribute doesn't exist
		if hasattr(message, "subject"):
			subject = message.subject
		else:
			subject = ''

		is_html = True
		html_body = ''
		plain_body = ''
		message_body = ''
		bodies = message.bodies()
		for content_type, body in bodies:
			if content_type == 'text/plain':
				is_html = False
				plain_body += body.decode()
			else:
				html_body += body.decode()

		if is_html:
			message_body = html_body
		else:
			message_body = plain_body

		return (sender, message_body, is_html, html_body, plain_body, subject)

	def handle_signature(self, message):
		""" The user is setting their signature via blank email. """
		(sender, message_body, is_html, html_body, plain_body, subject) = self.parse_message(message)

		user = db.Query(Users).filter('pt_emails =', sender).get()

		if user is None:
			self.log_and_reply(sender, "Could not find your user. Have you signed up and set up your email yet?\n\n" +
				"You can sign up at ptreply.com.\n\n" +
				"Your signature will not be added.\n\nYour original email:\n%s" % (message_body))
			return

		#strip appropriately
		plain_body = plain_body.strip()

		strip_html = re.compile('^(\s*<br\s*/?>)*\s*|(\s*<br\s*/?>)*\s*$', re.I)
		html_body = strip_html.sub(html_body, '')

		reply = ''
		error = False
		(code, message) = ModelsUtil.add_signature(user, html_body)
		if code != 200:
			error = True
			reply = "Your HTML signature was not added. Reason: %s" % (message)
		else:
			reply = "The following HTML signature was added:\n%s" % (html_body)

		(code, message) = ModelsUtil.add_signature(user, plain_body)
		if code != 200:
			error = True
			reply = "%s\n========\nYour plain text signature was not added. Reason: %s" % (reply, message)
		else:
			reply = "%s\n========\nThe following plain text signature was added:\n%s" % (reply, plain_body)

		mail.send_mail(sender=self.noreply, to=sender, subject="PT Reply Signature", body=reply)

	def handle_comment(self, message):
		""" The user is posting a comment to Pivotal Tracker via email. """
		(sender, message_body, is_html, html_body, plain_body, subject) = self.parse_message(message)
		logging.info('is_html = %s', is_html)
		if is_html == True:
			# try to clean up the html
			message_body = self.strip_and_clean(message_body)

		user = db.Query(Users).filter('pt_emails =', sender).get()

		if user is None:
			self.log_and_reply(sender, "Could not find your Pivotal Tracker token. Have you signed up yet? " +
				"Your comment will not be added.\n\nYour original email:\n%s" % (message_body))
			return

		mytoken = user.pt_token

		story_id = self.get_story_id(message_body)

		if story_id == False:
			self.log_and_reply(sender,
				"Could not find the story Id. Your comment will not be added.\n\nYour original email:\n%s" % (
					message_body))
			return

		project_name = self.get_name_from_subject(subject)
		project_id = PTUtil.get_project_id(user, project_name, story_id)

		if project_id != False:
			logging.info("Using ProjectId: " + project_id + " StoryId: " + story_id)
		else:
			self.log_and_reply(sender,
				"Could not find the project for this story. Your comment will not be added.\n\nYour original email:\n%s" % (
					message_body))
			return

		comment = self.get_pt_comment(message_body, user.signatures, is_html)
		if comment is None:
			self.log_and_reply(sender, "Could not figure out what your comment was.\n\nYour original email:\n%s" % (
				message_body))
			return

		self.post_to_pt(mytoken, project_id, story_id, comment)

		comment = Comments(user_id = user.user_id, project_id = project_id, story_id = story_id,
			comment = db.Text(comment))
		db.put(comment)

	def strip_and_clean(self, html):
		""" Cleans up the HTML structure and strips all tags. """
		html = "".join([line.strip() for line in html.split("\n")])
		html = re.sub('<!DOCTYPE.*?>', '', html)
		html = StringUtil.br2nl(html)

		# strip html
		html = ''.join(BeautifulSoup(html).findAll(text=True))

		return html

	def log_and_reply(self, sender, error):
		"""
		Logs an error to the App Engine console and emails the user to notify them of what happened.

		If self.error_recipients is set, will send a copy of the email to all addresses in that list as well.
		"""
		logging.error(error)
		mail.send_mail(sender=self.noreply, to=sender, subject=self.error_subject, body=error)
		if len(self.error_recipients) > 0:
			mail.send_mail(sender=self.noreply, to=self.error_recipients, subject=self.error_subject, body=error)

	def get_name_from_subject(self, subject):
		""" Parses the project name out of a comment email """
		match = re.search('[A-Z\s]+\s\((.*)\):', subject)
		if match is not None:
			return match.group(1)
		else:
			return False

	def get_story_id(self, body):
		""" Parses and returns the story id from an email body. """
		match = re.search('http[s]?://www.pivotaltracker.com/story/show/(\d+)', body)
		if match is not None:
			return match.group(1)
		else:
			return False

	def get_pt_comment(self, body, signatures, is_html):
		""" Returns the part of the incoming email that is intended to be the Pivotal Tracker comment """
		if len(signatures) == 0:
			re_str = '(.*?)(?:(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)'
		else:
			signature_regex = ""
			for signature in signatures:
				if is_html:
					signature = self.strip_and_clean(signature)

				signature = re.escape(signature).replace('\\\r', '\n').replace(
					'\\\n', '\n').replace('\n', '(?:\\r|\\n)')
				if signature_regex != '':
					signature_regex = signature_regex + '|'
				signature_regex = signature_regex + signature

			re_str = '(.*?)(?:%s|(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)' % (signature_regex)

			logging.info(signature_regex)

		logging.info(re_str)

		comment = re.search(re_str, body, re.I | re.S)

		if comment is None:
			return None

		comment = comment.group(1)

		comment = re.sub('Begin forwarded message:', '', comment)
		comment = re.sub('On.*wrote:\n', '', comment)
		comment = re.sub('_+\n', '', comment)
		comment = re.sub('\n\n+', '\n\n', comment)

		return comment

	def post_to_pt(self, token, project_id, story_id, comment):
		""" post the user's comment to the Pivotal Tracker story """
		note = "<note><text>"+comment+"</text></note>"

		data = note

		url = "http://www.pivotaltracker.com/services/v3/projects/"+project_id+"/stories/"+story_id+"/notes"
		result = urlfetch.fetch(url=url,
						payload=data,
						method=urlfetch.POST,
						headers={'X-TrackerToken': token, 'Content-type': 'application/xml'})

		note_dom = minidom.parseString(result.content)
		note_id = None
		for node in note_dom.getElementsByTagName('note'):
			note_id = node.getElementsByTagName('id')[0].firstChild.data

		if note_id is not None:
			logging.info("Comment Posted")
		else:
			logging.info("Failed to Post Comment")
			logging.info(result.content)

