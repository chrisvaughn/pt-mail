"""
module util defines useful utilities
"""
import logging, re
from xml.dom import minidom
from django.utils import simplejson as json
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import db

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

	@staticmethod
	def damerau_levenshtein(seq1, seq2):
		"""Calculate the Damerau-Levenshtein distance between sequences.
		(taken from: http://mwh.geek.nz/tag/damerau-levenshtein/)

		This distance is the number of additions, deletions, substitutions,
		and transpositions needed to transform the first sequence into the
		second. Although generally used with strings, any sequences of
		comparable objects will work.

		Transpositions are exchanges of *consecutive* characters; all other
		operations are self-explanatory.

		This implementation is O(N*M) time and O(M) space, for N and M the
		lengths of the two sequences.

		>>> damerau_levenshtein('ba', 'abc')
		2
		>>> damerau_levenshtein('fee', 'deed')
		2

		It works with arbitrary sequences too:
		>>> damerau_levenshtein('abcd', ['b', 'a', 'c', 'd', 'e'])
		2
		"""
		# codesnippet:D0DE4716-B6E6-4161-9219-2903BF8F547F
		# Conceptually, this is based on a len(seq1) + 1 * len(seq2) + 1 matrix.
		# However, only the current and two previous rows are needed at once,
		# so we only store those.
		oneago = None
		thisrow = range(1, len(seq2) + 1) + [0]
		for x in xrange(len(seq1)):
			# Python lists wrap around for negative indices, so put the
			# leftmost column at the *end* of the list. This matches with
			# the zero-indexed strings and saves extra calculation.
			twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
			for y in xrange(len(seq2)):
				delcost = oneago[y] + 1
				addcost = thisrow[y - 1] + 1
				subcost = oneago[y - 1] + (seq1[x] != seq2[y])
				thisrow[y] = min(delcost, addcost, subcost)
				# This block deals with transpositions
				if (x > 0 and y > 0 and seq1[x] == seq2[y - 1]
					and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
					thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
		return thisrow[len(seq2) - 1]

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
	def get_project_names(user, use_cache = True):
		""" Gets the project names from cache (if exists), otherwise fetches from API. """
		# Check Memcache for users Project List """
		data = memcache.get(user.user_id+'_projects')
		if use_cache and data is not None:
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

		project_names = []
		for node in project_dom.getElementsByTagName('project'):
			name = node.getElementsByTagName('name')[0].firstChild.data
			project_names.append(name)

		return project_names

	@staticmethod
	def get_project_id(user, project_name, story_id = None):
		"""
		First check if storyId to projectID is already in cache
		Next check if the users projects lists are in cache
		If not, fetch the list from API
		loop through the list of projects until you find a match
		  with the project name from the email subject
		if not found and cache was used fetch the project list from API
		loop through the list and make request with storyId until we get a 200
		"""

		# Check Memcache for StoryId
		if story_id is not None:
			data = memcache.get("project_id_for_" + story_id)
			if data is not None:
				logging.info("Found the story_id in cache")
				return data

		# Check Memcache for users Project List
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
					if story_id is not None:
						memcache.set("project_id_for_" + story_id, project_id)
					return project_id

		# if we got here and couldn't find it then maybe cache is old
		if caching_used:
			result = urlfetch.fetch(url="http://www.pivotaltracker.com/services/v3/projects",
			headers={'X-TrackerToken': user.pt_token})
			if result.status_code == 200:
				project_dom = minidom.parseString(result.content)
				memcache.set(user.user_id+'_projects', result.content, 60*60*24*7)
			else:
				logging.info("Could not fetch users projects from the API")
				return False

		# we didn't find the project id by comparing the name so lets check each id with the story id
		if story_id is not None:
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
