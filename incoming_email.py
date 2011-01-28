import logging, email, re
from google.appengine.ext import webapp
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from xml.dom import minidom
import urllib
from google.appengine.ext import db
from models import Tokens
from models import Users
from models import Comments
from google.appengine.api import mail

# use Beautiful Soup to strip html (or parse it later if we want)
from BeautifulSoup import BeautifulSoup

class IncomingEmailHandler(InboundMailHandler):

    noreply="PT-Mail <noreply@pt-mail.appspotmail.com>"

    def receive(self, message):
        p = re.compile('([-a-z0-9_.+]+@([-a-z0-9]+\.)+[a-z]{2,6})',re.IGNORECASE)
        m = p.search(message.sender)
        if m is not None:
            sender = m.group(1)
        else:
            logging.error("couldn't find sender")
            return

        sender = sender.lower()
        logging.info("Received a message from: " + sender)

        message_body = ''
        bodies = message.bodies('text/plain')
        for content_type, body in bodies:
            message_body += body.decode()
        if message_body == '':
            logging.info("no text/plain found, checking html")

            bodies = message.bodies('text/html')
            for content_type, body in bodies:
                message_body += body.decode()

            # try to clean up the html
            message_body = self.stripAndClean(message_body)
		
        user = db.Query(Users).filter('pt_emails =', sender).get()
		
        if user is None:
            self.logAndReply(sender, "Could not find your PT token. Have you signed up yet? Your comment will not be added.\n\nOriginal reply:\n%s" % (message_body))
            return
            
        mytoken = user.pt_token

        storyId = self.getStoryId(message_body)

        if storyId == False:
            self.logAndReply(sender, "Could not find the story Id. Your comment will not be added.\n\nOriginal reply:\n%s" % (message_body))
            return

        projectId = self.getProjectIdFromStoryId(mytoken, storyId)

        if projectId != False:
            logging.info("Using ProjectId: " + projectId + " StoryId: " + storyId)
        else:
            self.logAndReply(sender, "Could not find the project for this story. Your comment will not be added.\n\nOriginal reply:\n%s" % (message_body))
            return

        comment = self.getComment(message_body, user.signatures)
        if comment is None:
            self.logAndReply(sender, "Could not figure out what your comment was.\n\nOriginal reply:\n%s" % (message_body))
            return

        logging.info(comment)

        self.postToPT(mytoken, projectId, storyId, comment)
        
        comment = Comments(user_id=user.user_id, projectId=projectId, storyId=storyId, comment = db.Text(comment))        
        db.put(comment)

        return

    def stripAndClean(self, html):
        html = "".join([line.strip() for line in html.split("\n")])
        html = re.sub('<!DOCTYPE.*?>', '', html)
        html = re.sub('<(?:br|BR)\s*/?>', lambda x: "\n", html)

        # strip html
        html = ''.join(BeautifulSoup(html).findAll(text=True))

        return html

    def logAndReply(self, sender, error):
        logging.error(error)
        mail.send_mail(sender=self.noreply, to=sender, subject="PT-Mail Error", body=error)
        mail.send_mail(sender=self.noreply, to=('kevin.morey@gmail.com', 'chrisvaughn01@gmail.com'), subject="PT-Mail Error", body=error)

    def getStoryId(self, body):
        m = re.search('http[s]?://www.pivotaltracker.com/story/show/(\d+)', body)
        if m is not None:
            return m.group(1)
        else:
            return False


    def getProjectIdFromStoryId(self, token, storyId):
        result = urlfetch.fetch(url="http://www.pivotaltracker.com/services/v3/projects",
                        headers={'X-TrackerToken': token})
        if result.status_code == 200:
            projectDOM = minidom.parseString(result.content)
        else:
            return False

        for node in projectDOM.getElementsByTagName('project'):
            projectId = node.getElementsByTagName('id')[0].firstChild.data

            url = "http://www.pivotaltracker.com/services/v3/projects/"+projectId+"/stories/"+storyId
            result = urlfetch.fetch(url=url,
                        headers={'X-TrackerToken': token})

            storyDOM = minidom.parseString(result.content)
            for sNode in storyDOM.getElementsByTagName('story'):
                if storyId == sNode.getElementsByTagName('id')[0].firstChild.data:
                    return projectId

        return False

    def getComment(self, body, signatures):

        if len(signatures) == 0:
            re_str = '(.*?)(?:(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)'
        else:
            signature_regex = ""
            for signature in signatures:
               signature = self.stripAndClean(signature)	
               signature = re.escape(signature).replace('\\\r', '\n').replace('\\\n', '\n').replace('\n', '(?:\\r|\\n)')
               if signature_regex != '':
	               signature_regex = signature_regex + '|'
               signature_regex = signature_regex + signature
            logging.info(signature_regex)
            re_str = '(.*?)(?:%s|(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)' % (signature_regex)

        comment = re.search(re_str, body, re.I | re.S)

        if comment is None:
            return None

        comment = comment.group(1)

        comment = re.sub('Begin forwarded message:', '', comment)
        comment = re.sub('On.*wrote:\n', '', comment)
        comment = re.sub('_+\n', '', comment)
        comment = re.sub('\n\n+', '\n\n', comment)

        return comment

    def postToPT(self, token, projectId, storyId, comment):
        note = "<note><text>"+comment+"</text></note>"

        data = note

        url = "http://www.pivotaltracker.com/services/v3/projects/"+projectId+"/stories/"+storyId+"/notes"
        result = urlfetch.fetch(url=url,
                        payload=data,
                        method=urlfetch.POST,
                        headers={'X-TrackerToken': token, 'Content-type': 'application/xml'})

        noteDOM = minidom.parseString(result.content)
        noteId = None
        for node in noteDOM.getElementsByTagName('note'):
            noteId = node.getElementsByTagName('id')[0].firstChild.data

        if noteId is not None:
            logging.info("Comment Posted")
        else:
            logging.info("Failed to Post Comment")
            logging.info(result.content)

