"""
module util defines useful utilities
"""
import logging, re
from xml.dom import minidom
from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import users as google_users
from google.appengine.ext import db
from models import Users

class StringUtil():
	""" string utilities """

	@staticmethod
	def nl2br(string):
		""" converts newline (\n) to html breaks (<br />) """
		return '<br />\n'.join(string.split('\n'))

	@staticmethod
	def br2nl(string):
		"""
		converts html breaks (<br />) to newlines (\n)
		handles br flexibly: <br>, <br />, <BR>, etc.
		"""
		return re.sub('<(?:br|BR|bR|Br)\s*/?>', lambda x: "\n", string)

class ModelsUtil():
	""" Utilities to help with common model actions. """

	@staticmethod
	def add_signature(user, signature):
		"""
		Adds a signature to a User.
		Returns (400, <error>) if something fails.
		Returns (200, "[sig1, sig2, ... ]") on success.
		"""
		try:
			user.signatures.index(signature)
			return (400, 'Signature already added.')
		except ValueError:
			pass

		user.signatures.append(db.Text(signature))
		db.put(user)
		sigs = []
		for signature in user.signatures:
			sigs.append(StringUtil.nl2br(signature))

		return (200, json.dumps(sigs))

class PTUtil():
	""" Utilities for common interactions with PT API """
	
	@staticmethod
	def get_project_id(user, project_name, story_id):
		""" 
		First check if storyId to projectID is already in cache
		Next check if the users projects lists are in cache
		If not, fetch the list from API
		loop through the list of projects until you find a match
		  with the project name from the email subject
		if not found and cache was used fetch the project list from API
		loop through the list and make request with storyId until we get a 200
		"""
	
		""" Check Memcache for StoryId"""
		data = memcache.get("project_id_for_" + story_id)
		if data is not None:
			logging.info("Found the story_id in cache")
			return data
		
		""" Check Memcache for users Project List """
		caching_used = False
		data = memcache.get(user.user_id+'_projects')
		if data is not None:
			logging.info("Using cached projects list for user")
			project_dom = minidom.parseString(data)
			caching_used = True
		else:
			result = urlfetch.fetch(url="http://www.pivotaltracker.com/services/v3/projects", 
			headers={'X-TrackerToken': user.pt_token})
			if result.status_code == 200:
				project_dom = minidom.parseString(result.content)
				memcache.set(user.user_id+'_projects', result.content, 60*60*24*7)
			else:
				logging.info("Could not fetch users projects from the API")
				return False
		
		if project_name != False:
			for node in project_dom.getElementsByTagName('project'):
				name = node.getElementsByTagName('name')[0].firstChild.data
				project_id = node.getElementsByTagName('id')[0].firstChild.data
				logging.info('Checking: ' + project_name + ' against ' + name)
				if project_name.lower() == name.lower():
					memcache.set("project_id_for_" + story_id, project_id)
					return project_id
		
		""" if we got here and couldn't find it then maybe cache is old """
		if caching_used:
			result = urlfetch.fetch(url="http://www.pivotaltracker.com/services/v3/projects", 
			headers={'X-TrackerToken': user.pt_token})
			if result.status_code == 200:
				project_dom = minidom.parseString(result.content)
				memcache.set(user.user_id+'_projects', result.content, 60*60*24*7)
			else:
				logging.info("Could not fetch users projects from the API")
				return False
			
		""" we didn't find the project id by comparing the name so lets check each id with the story id """			
		logging.info("Looping through all projects and requesting story id")
		for node in project_dom.getElementsByTagName('project'):
			project_id = node.getElementsByTagName('id')[0].firstChild.data
			url = "http://www.pivotaltracker.com/services/v3/projects/"+project_id+"/stories/"+story_id
			result = urlfetch.fetch(url=url,
						headers={'X-TrackerToken': user.pt_token})
			story_dom = minidom.parseString(result.content)
			for story_node in story_dom.getElementsByTagName('story'):
				if story_id == story_node.getElementsByTagName('id')[0].firstChild.data:
					memcache.set("project_id_for_" + story_id, project_id)
					return project_id
		
		logging.info("Could not find the project id using any method.")
		return False
