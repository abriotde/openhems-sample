"""
Usefull to get informations from pyproject.toml
"""

from pathlib import Path
import toml


class ProjectConfiguration:
	"""
	Usefull function to do something like a cast : Convertion of types
	"""

	def __init__(self, openHemsProjectConfPath=None):
		if openHemsProjectConfPath is None:
			# openHemsProjectConfPath = Path(__file__).parents[4] / "pyproject.toml"
			for path in Path(__file__).parents:
				openHemsProjectConfPath = path / "pyproject.toml"
				if openHemsProjectConfPath.is_file():
					break
		with openHemsProjectConfPath.open('r', encoding="utf-8") as file:
			self._conf = toml.loads(file.read())

	def getVersion(self):
		"""
		Return current project version.
		"""
		return self._conf['project']['version']

	def getMaintainers(self):
		"""
		Return current project maintainers.
		"""
		return self._conf['project']['maintainers']

	def getUrls(self):
		"""
		get projects urls
		"""
		return self._conf['project']['urls']

	def getLicence(self):
		"""
		Get Licence
		"""
		return "GPL-3.0-or-later"

	def getName(self):
		"""
		Get project name
		"""
		return "OpenHEMS"
