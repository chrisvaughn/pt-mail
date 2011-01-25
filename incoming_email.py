import logging, email, re
from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from xml.dom import minidom
import urllib
from google.appengine.ext import db
from models import Tokens
from models import Comments
from google.appengine.api import mail

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
        
        plaintext_bodies = message.bodies('text/plain')
        message_body = ''
        for content_type, body in plaintext_bodies:
            message_body += body.decode()
            
        tokens = db.Query(Tokens).filter('pt_emails =', sender).get()
        
        if tokens is None:
            self.logAndReply(sender, "Could not find your PT token. Have you signed up yet? Your comment will not be added.\n\nOriginal reply:\n%s" % (message_body))
            return
            
        mytoken = tokens.pt_token

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

        if tokens.signature is None:
            signature = ''
        else:
            signature = tokens.signature
            
        comment = self.getComment(message_body, signature)
        if comment is None:
            self.logAndReply(sender, "Could not figure out what your comment was.\n\nOriginal reply:\n%s" % (message_body))
            return
            
        logging.info(comment)
            
        self.postToPT(mytoken, projectId, storyId, comment)
        
        comment = Comments(token=tokens, projectId=projectId, storyId=storyId, comment = db.Text(comment))        
        db.put(comment)

        return
            
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
    
    def getComment(self, body, signature):
        
        if signature is None or signature == "":
            re_str = '(.*?)(?:(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)'
        else:
            signature = re.escape(signature).replace('\\\r', '\n').replace('\\\n', '\n').replace('\n', '(?:\\r|\\n)')
            re_str = '(.*?)(?:%s|(?:\\r|\\n)>|From: Pivotal Tracker|(?:\\r|\\n)On .*? wrote:|Begin forwarded message:)' % (signature)
        
        comment = re.search(re_str, body, re.I | re.S)
        
        if comment is None:
            return None
            
        comment = comment.group(1)

        ### OLD CODE
        # lines = body.split('\n')
        #         comment = ''
        #         
        #         for line in lines:
        #             
        #             m = re.search('^>|From: Pivotal Tracker|^On .*?\n?.*? wrote:$', line)
        #             #m2 = re.search('From: Pivotal Tracker', line)
        #             
        #             if m is None: # and m2 is None:
        #                 line += '\n'
        #                 comment += line
        #             else:
        #                 break
        #

        #if user has a signature stored then remove it (if it wasn't matched)
        #comment = re.sub(signature, '', comment)

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
        
        