
import os
import logging
import base64
import urllib
from django.utils import simplejson as json
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.api import users as googleUsers
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from xml.dom import minidom
from incoming_email import IncomingEmailHandler
from models import Tokens
from models import Users


class MainHandler(webapp.RequestHandler):
    def get(self):
    
        d = {}
        if googleUsers.get_current_user():
            googleUser = googleUsers.get_current_user()
            user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()
            
            if user is not None: 
                if user.pt_token is not None:
                    d['havetoken'] = True
                else:
                    d['havetoken'] = False
                
                if user.pt_emails is not None:
                    d['emails'] = user.pt_emails
                    
                if len(user.signatures) > 0:
                	d['signature'] = user.signatures[0]
        
            d['url'] = googleUsers.create_logout_url(self.request.uri)
            d['user'] = googleUsers.get_current_user()
        else:
            d['url'] = googleUsers.create_login_url(self.request.uri)

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, d))

class GetToken(webapp.RequestHandler):
    def post(self):
        googleUser = googleUsers.get_current_user()
        user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()            
        if user is None:
            user = Users(user_id = googleUser.user_id(), email = googleUser.email())
        
        url='https://www.pivotaltracker.com/services/v3/tokens/active'
        username = self.request.get('username')
        password = self.request.get('password')
        base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
        authheader =  "Basic %s" % base64string
        result = urlfetch.fetch(url=url,
                        headers={"Authorization": authheader})
        if result.status_code == 200:
            tokenDOM = minidom.parseString(result.content)
            
            for node in tokenDOM.getElementsByTagName('token'):
                tokenId = node.getElementsByTagName('guid')[0].firstChild.data
                
            user.pt_username = self.request.get('username')
            user.pt_token = tokenId
            
            db.put(user)
            
        elif result.status_code == 401:
            self.response.out.write("Invalid Username or Password")
            self.response.set_status(401)
        else:
            self.response.out.write("Error getting token. Please try again later")
            self.response.set_status(400)

class RemoveToken(webapp.RequestHandler):
    def post(self):
        googleUser = googleUsers.get_current_user()
        user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()            
        if user is not None:
            user.delete()
            user = Users(user_id = googleUser.user_id(), email = googleUser.email())
        else:
            self.response.out.write("Error getting user.")
            self.response.set_status(400)
        
class SaveEmail(webapp.RequestHandler):
    def post(self):
        googleUser = googleUsers.get_current_user()
        user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()            
        if user is None:
            user = Users(user_id = googleUser.user_id(), email = googleUser.email())
    
        email = self.request.get('email')
        email = email.lower()

        if email == "":
            self.response.set_status(400)
            self.response.out.write('Email is required.')
            return
            
        try:
            idx = user.pt_emails.index(email)
            self.response.set_status(400)
            self.response.out.write('Email already added')
            return
        except:
            pass
        
        user.pt_emails.append(email)
        db.put(user)
        self.response.out.write(json.dumps(user.pt_emails))
        
class RemoveEmail(webapp.RequestHandler):
    def post(self):
        googleUser = googleUsers.get_current_user()
        user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()            
        if user is None:
            user = Users(user_id = googleUser.user_id(), email = googleUser.email())
    
        email = self.request.get('email')
        email = email.lower()
        user.pt_emails.remove(email)

        db.put(user)
        self.response.out.write(json.dumps(user.pt_emails))
        
        self.response.out.write("{success:true}")
                
class SaveSignature(webapp.RequestHandler):
    def post(self):
        googleUser = googleUsers.get_current_user()
        user = db.Query(Users).filter('user_id =', googleUser.user_id()).get()            
        if user is None:
            user = Users(user_id = googleUser.user_id(), email = googleUser.email())
    
        signature = self.request.get('signature')
        user.signatures.append(db.Text(signature))
        db.put(user)
        
        
class UpdateSchema(webapp.RequestHandler):
	def get(self):
		tokens = db.Query(Tokens).fetch(1000)
		
		for token in tokens:
			user = Users(user_id = token.user_id, email = token.email, pt_username = token.pt_username, pt_emails = token.pt_emails, pt_token = token.pt_token)
			user.signatures.append(token.signature)
			db.put(user)

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/get-token', GetToken),
                                          ('/remove-token', RemoveToken),
                                          ('/save-email', SaveEmail),
                                          ('/remove-email', RemoveEmail),
                                          ('/save-signature', SaveSignature),
										  ('/update-schema', UpdateSchema),
                                          IncomingEmailHandler.mapping()
                                         ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
