"""
Usefull to get informations from pyproject.toml
"""

from pathlib import Path
import toml # pylint: disable=E0401
ROOT_DIR = Path(__file__).parents[2]
# In your openhems/__init__.py
from importlib.metadata import version, metadata

__version__ = version("openhems")
# or read other metadata:
name = metadata("openhems")["Name"]
class ProjectConfiguration:
	"""
	Usefull function to do something like a cast : Convertion of types
	"""

	def __init__(self, openHemsProjectConfPath=None):
		# In your openhems/__init__.py
			self._version = version("openhems")
			self._conf = metadata("openhems")

	def getVersion(self):
		"""
		Return current project version.
		"""
		return self._version

	def getMaintainers(self):
		"""
		Return current project maintainers.
		"""
		print("Project configuration:", self._conf)
		return self._conf.get('Maintainer', 'Unknown')

	def getUrls(self):
		"""
		get projects urls
		"""
		url_entries = self._conf.get_all('Project-URL')
		all_urls = {}
		for entry in url_entries:
			label, url = entry.split(", ", 1)
			all_urls[label] = url
		return all_urls

	def getConf(self):
		"""
		get all configurations
		"""
		return self._conf

	def getLicence(self):
		"""
		Get Licence
		"""
		return "GPL-3.0-or-later"

	def getContact(self):
		"""
		Get contact information
		"""
		return self._conf.get('Maintainer-email', 'Unknown')

	def getName(self):
		"""
		Get project name
		"""
		return self._conf['Name']
