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

class IncomingEmailHandler(InboundMailHandler):

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
        tokens = db.Query(Tokens).filter('pt_email =', sender).get()
        mytoken = tokens.pt_token
        
        plaintext_bodies = message.bodies('text/plain')
    
        message_body = ''
        for content_type, body in plaintext_bodies:
            message_body += body.decode()

        storyId = self.getStoryId(message_body)  
        
        if storyId == False:
            logging.info("Could not find the story Id. Your comment will not be added")
        	return          

        projectId = self.getProjectIdFromStoryId(mytoken, storyId)
    
        if projectId != False:
            logging.info("Using ProjectId: " + projectId + " StoryId: " + storyId)
        else:
            logging.info("Could not find the project for this story. Your comment will not be added")

        if tokens.signature is None:
            signature = ''
        else:
            signature = tokens.signature
			
        comment = self.getComment(message_body, signature)
        logging.info(comment)
            
        self.postToPT(mytoken, projectId, storyId, comment)
        
        comment = Comments(token=tokens, projectId=projectId, storyId=storyId, comment = db.Text(comment))
        
        db.put(comment)
        
        return
            
            
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
        
        lines = body.split('\n')
        comment = ''
        
        for line in lines:
            
            m = re.search('^>', line)
            m2 = re.search('From: Pivotal Tracker', line)
            
            if m is None and m2 is None:
                line += '\n'
                comment += line
            else:
                break
            
        #if user has a signature stored then remove it
        comment = re.sub(signature, '', comment)

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
        
        