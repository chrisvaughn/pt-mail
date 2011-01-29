"""
module util defines useful utilities
"""
import re

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
