"""
Usefull to get informations from pyproject.toml
"""

from pathlib import Path
import toml # pylint: disable=E0401
ROOT_DIR = Path(__file__).parents[2]
# In your openhems/__init__.py
from importlib.metadata import version, metadata, PackageNotFoundError

# or read other metadata:
class ProjectConfiguration:
	"""
	Usefull function to do something like a cast : Convertion of types
	"""

	def __init__(self, openHemsProjectConfPath=None):
		# In your openhems/__init__.py
		try:
			self._mode = 1
			self._version = version("openhems")
			self._conf = metadata("openhems")
		except PackageNotFoundError:
			# case we run project as standalone
			# No metadata will be found
			self._mode = 0
			conf = self.get_conf_from_pyproject()
			project = conf.get("project", {})
			self._version = project.get("version",0.3)
			self._conf = project

	def get_conf_from_pyproject(self):
		"""
		Get the project configuration from pyproject.toml file instead of metadata (When not installed)
		"""
		openHemsProjectConfPath = Path(__file__)
		for path in Path(__file__).parents:
			openHemsProjectConfPath = path / "pyproject.toml"
			if openHemsProjectConfPath.is_file():
				break
		else:
			return {}
		with openHemsProjectConfPath.open('r', encoding="utf-8") as file:
			return toml.loads(file.read())

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
		if self._mode==1:
			return self._conf.get('Maintainer', 'Unknown')
		else:
			return self._conf['maintainers']

	def getUrls(self):
		"""
		get projects urls
		"""
		if self._mode==1:
			url_entries = self._conf.get_all('Project-URL')
			all_urls = {}
			for entry in url_entries:
				label, url = entry.split(", ", 1)
				all_urls[label] = url
			return all_urls
		else:
			return self._conf['urls']

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
		if self._mode==1:
			return self._conf.get('Maintainer-email', 'Unknown')
		else:
			return self._conf['maintainers'][0]['email']

	def getName(self):
		"""
		Get project name
		"""
		if self._mode==1:
			return self._conf['Name']
		else:
			return self._conf['name']

