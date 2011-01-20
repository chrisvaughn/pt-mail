
import os
import logging
import base64
import urllib
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from xml.dom import minidom
from incoming_email import IncomingEmailHandler
from models import Tokens


class MainHandler(webapp.RequestHandler):
    def get(self):
    
        d = {}
        if users.get_current_user():
            user = users.get_current_user()
            token = db.Query(Tokens).filter('user_id =', user.user_id()).get()            
            if token is not None: 
                if token.pt_token is not None:
                    d['havetoken'] = True
                else:
                    d['havetoken'] = False
                
                if token.pt_email is not None:
                    d['email'] = token.pt_email
                    
                if token.signature is not None:
                	d['signature'] = token.signature
        
            d['url'] = users.create_logout_url(self.request.uri)
            d['user'] = users.get_current_user()
        else:
            d['url'] = users.create_login_url(self.request.uri)

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, d))

class GetToken(webapp.RequestHandler):
    def post(self):
        user = users.get_current_user()
        token = db.Query(Tokens).filter('user_id =', user.user_id()).get()            
        if token is None:
            token = Tokens(user_id = user.user_id(), email = user.email())
        
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
                
            token.pt_username = self.request.get('username')
            token.pt_token = tokenId
            
            db.put(token)
            
        elif result.status_code == 401:
			self.response.out.write("Invalid Username or Password")
			self.response.set_status(401)
        else:
            self.response.out.write("Error getting token. Please try again later")
            self.response.set_status(400)
        
        
class SaveEmail(webapp.RequestHandler):
    def post(self):
        user = users.get_current_user()
        token = db.Query(Tokens).filter('user_id =', user.user_id()).get()            
        if token is None:
            token = Tokens(user_id = user.user_id(), email = user.email())
    
        email = self.request.get('email')
        email = email.lower()
        token.pt_email = email
        db.put(token)
        
class SaveSignature(webapp.RequestHandler):
    def post(self):
        user = users.get_current_user()
        token = db.Query(Tokens).filter('user_id =', user.user_id()).get()            
        if token is None:
            token = Tokens(user_id = user.user_id(), email = user.email())
    
        signature = self.request.get('signature')
        token.signature = db.Text(signature)
        db.put(token)


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/gettoken', GetToken),
                                          ('/saveemail', SaveEmail),
                                          ('/savesignature', SaveSignature),
                                          IncomingEmailHandler.mapping()
                                         ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
