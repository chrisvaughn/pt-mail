"""
module util defines useful utilities
"""
import re
from django.utils import simplejson as json
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
