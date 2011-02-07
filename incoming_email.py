"""
incoming_email module handles any email delivered to the app engine site.
"""
import logging, re, sys
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
	newreply = "PT Reply <new@ptreply.com>"
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
		elif addressed_to == 'new':
			self.new_ticket(message)
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
		html_body = re.sub('^(\s*<br[^>]*>\s*)+|(\s*<br[^>]*>\s*)+$', lambda x: '', html_body)

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

	# TODO refactor new_ticket ... to many return statements
	def new_ticket(self, message):
		""" The user is creating a new ticket in Pivotal Tracker via email. """
		(sender, message_body, is_html, html_body, plain_body, subject) = self.parse_message(message)
		logging.info('is_html = %s', is_html)
		if is_html == True:
			# try to clean up the html
			message_body = self.strip_and_clean(message_body)

		# clean up subject
		pattern = re.compile('^\s*re[\s:]+', re.I)
		subject = pattern.sub(lambda x: '', subject)

		# clean up message body
		pattern = re.compile('##### PT REPLY #####.*##### PT REPLY #####', re.I | re.S)
		message_body = pattern.sub(lambda x: ' ', message_body).strip()

		user = db.Query(Users).filter('pt_emails =', sender).get()

		if user is None:
			self.log_and_reply(sender,
				"##### PT REPLY #####\n" +
				"Could not find your Pivotal Tracker token. Have you signed up yet at ptreply.com? \n\n" +
				"Your story will not be added.\n" +
				"\nNote: this section will automatically be removed when you reply.\n" +
				"##### PT REPLY #####\n\n" + message_body)
			return

		token = user.pt_token

		bad_subject = False
		index = subject.find(':')
		if index < 0:
			# error no colon in subject
			bad_subject = True

		temp = subject[:index]
		story_name = subject[index+1:].strip()

		index = temp.rfind(' ')
		if index < 0:
			# error no space in subject
			bad_subject = True
			return

		if bad_subject == True:
			self.log_and_reply(sender,
				"##### PT REPLY #####\n" +
				"Your subject was confusing, please make sure it is in the following format:\n" +
				"  PROJECT_NAME STORY_TYPE: STORY_TITLE\n" +
				"  (Example: PT-MAIL bug: users can't login)\n" +
				"\nNote: this section will automatically be removed when you reply.\n" +
				"##### PT REPLY #####\n\n" + message_body, subject=subject, send_from=self.newreply, debug=False)
			return

		possible_project = temp[:index]
		story_type = temp[index+1:].lower()

		logging.info("possible_project: %s, story_type: %s", possible_project, story_type)

		projects, distance = self.guess_name_from_subject(user, possible_project)
		logging.info("projects = %s, distance = %s", projects, distance)

		if len(projects) == 0:
			# ERROR couldn't find any projects
			self.log_and_reply(sender,
				"##### PT REPLY #####\n" +
				"We couldn't find any projects in Pivotal Tracker that match your subject. " +
				"Please double check for typos in your subject and try again.\n" +
				"\nNote: this section will automatically be removed when you reply.\n" +
				"##### PT REPLY #####\n\n" + message_body, subject=subject, send_from=self.newreply, debug=False)
			return

		if len(projects) > 1 and distance == 0:
			# FATAL ERROR more than one project name matched EXACTLY, we cannot continue
			self.log_and_reply(sender,
				"##### PT REPLY #####\n" +
				"More than one project in Pivotal Tracker matched your subject EXACTLY.\n" +
				"\nThis is either because our guessing algorithm is wrong or you are actually a member " +
				"of more than one project with the same name. If you only have one project with this name, " +
				"please email us at support@ptreply.com so we can take a look.\n" +
				"\nNote: this section will automatically be removed when you reply.\n" +
				"##### PT REPLY #####\n\n" + message_body, subject=subject, send_from=self.newreply, debug=False)
			return

		if len(projects) > 1 or distance > 2:
			# ERROR more than one project matched the same or not well enough, user needs to choose
			new_subject = "%s %s: %s" % (projects[0], story_type, story_name)

			self.log_and_reply(sender,
				"##### PT REPLY #####\n" +
				"We couldn't guess what project you wanted to add this story to, but we think we have a pretty good idea.\n" +
				"\nCheck the new subject of this email, and if it looks good, just hit reply and send and we'll take care of it.\n" +
				"\nHere are some other projects it might be, but you'll have to change the subject yourself:\n " +
				"\n ".join(projects[1:]) + "\n" +
				"\nNote: this section will automatically be removed when you reply.\n" +
				"##### PT REPLY #####\n\n" + message_body, subject=new_subject, send_from=self.newreply, debug=False)
			return

		project_id = PTUtil.get_project_id(user, projects[0])

		if project_id == False:
			self.log_and_reply(sender, "##### PT REPLY #####\n" +
				"Could not find the project in Pivotal Tracker.\n" +
				"\nPlease visit ptreply.com and verify that your token is still valid.\n" +
				"##### PT REPLY #####\n\n" + message_body)
			return

		# sanity check story type
		if story_type != 'feature' and story_type != 'bug' and story_type != 'release' and story_type != 'chore':
			story_type = 'feature'

		description = self.get_pt_comment(message_body, user.signatures, is_html)

		payload = """
			<story>
				<story_type>%s</story_type>
				<name>%s</name>
				<description>%s</description>
			</story>
			""" % (story_type, story_name, description)

		logging.info("Using project_id %s to post new %s: %s", project_id, story_type, story_name)
		logging.info("Payload: %s", payload)

		url = "https://www.pivotaltracker.com/services/v3/projects/%s/stories" % (project_id)
		result = urlfetch.fetch(url=url,
			payload=payload,
			method=urlfetch.POST,
			headers={'X-TrackerToken': token, 'Content-type': 'application/xml'})

		story_dom = minidom.parseString(result.content)
		story_id = None
		for node in story_dom.getElementsByTagName('story'):
			story_id = node.getElementsByTagName('id')[0].firstChild.data

		if story_id is not None:
			logging.info("Story Posted")
		else:
			logging.info("Failed to Post Story")
			logging.info(result.content)
			# TODO alert user

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

		self.post_reply_to_pt(mytoken, project_id, story_id, comment)

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

	def log_and_reply(self, sender, body, subject="PT Reply Error", send_from=noreply, debug=True):
		"""
		Logs an error to the App Engine console and emails the user to notify them of what happened.

		If self.error_recipients is set, will send a copy of the email to all addresses in that list as well.
		"""
		logging.error(body)
		mail.send_mail(sender=send_from, to=sender, subject=subject, body=body)
		if debug == True and len(self.error_recipients) > 0:
			mail.send_mail(sender=send_from, to=self.error_recipients, subject=subject, body=body)

	def guess_name_from_subject(self, user, subject):
		"""
		Looks through the users projects and tries to guess which one the subject is wanting. The subject should already
		be stripped down to the expected parts.
		Returns ([<closest_matches>], <damerau levenshtein value>)
		"""
		closest_match = ([], sys.maxint)

		project_names = PTUtil.get_project_names(user)
		if project_names == False:
			logging.error("couldn't get project names... croak!")
			return closest_match

		for project_name in project_names:
			distance = self.calc_word_distance(project_name.lower(), subject.lower())
			if distance == closest_match[1]:
				closest_match[0].append(project_name)
			elif distance < closest_match[1]:
				closest_match = ([project_name], distance)

		# TODO clear project cache and try again if no good match

		return closest_match

	def calc_word_distance(self, str1, str2):
		""" Compares the two strings using Damerau-Levenshtein distance.
		"""
		# strip non alpha-numeric
		str1 = re.sub('[^a-z0-9]', lambda x: ' ', str1.lower())
		str2 = re.sub('[^a-z0-9]', lambda x: ' ', str2.lower())

		# cleanup spaces
		str1 = re.sub(' {2,}', lambda x: ' ', str1)
		str2 = re.sub(' {2,}', lambda x: ' ', str2)

		distance = 0
		if len(str2) > len(str1):
			distance = StringUtil.damerau_levenshtein(str1, str2[:len(str1)])

		# this extra check is to "weight" the values against the full string...
		# for instance, given str1="abc" and str2="abc but there is more", we want this to return a higher distance
		# than if given str1="abc but" and str2="abc but there is more"
		distance += StringUtil.damerau_levenshtein(str1, str2)

		# TODO might want to do an additional check on the exact initial strings, since the stripping we do would
		# cause "ab-cd" and "ab.cd" to match exactly the same, which would be bad
		return distance

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

		if comment is not None:
			comment = comment.group(1)
		else:
			comment = body

		comment = re.sub('Begin forwarded message:', '', comment)
		comment = re.sub('On.*wrote:\n', '', comment)
		comment = re.sub('_+\n', '', comment)
		comment = re.sub('\n\n+', '\n\n', comment)

		return comment

	def post_reply_to_pt(self, token, project_id, story_id, comment):
		""" post the user's comment to the Pivotal Tracker story """
		note = "<note><text>"+comment+"</text></note>"

		data = note

		url = "https://www.pivotaltracker.com/services/v3/projects/"+project_id+"/stories/"+story_id+"/notes"
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

