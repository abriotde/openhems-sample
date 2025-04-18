#!/usr/bin/env python3
"""
Script to update OpenHEMS installation automatically.
"""

import os
import sys
from pathlib import Path
import re
import time
import functools
import importlib
from zipfile import ZipFile
import git # https://gitpython.readthedocs.io/en/stable/tutorial.html#submodule-handling
import requests
from packaging.version import Version
PATH_ROOT = Path(__file__).parents[1]
sys.path.append(str(PATH_ROOT))
from openhems.modules.util import ProjectConfiguration

postupdateScriptRegexp = re.compile('postupdate-(?P<version>[0-9.]*)\\.py')
gitCommitIdRegexp = re.compile('^[a-z0-9A-Z]{40}$')

def cmpVersions(a, b):
	"""
	Function to compare versions numbers (like 1.0.3 and 1.3.0)
	"""
	va = Version(a)
	vb = Version(b)
	if va<vb:
		return -1
	if va>vb:
		return 1
	return 0

class Updater:
	"""
	Updater to update OpenHEMS installation automatically
	"""
	@staticmethod
	def initFromEnv():
		"""
		Init Python variables from OS environment (instead of CLI arguments).
		"""
		path = os.environ.get('OPENHEMS_PATH')
		user = os.environ.get('OPENHEMS_USER', 'root')
		branch = os.environ.get('OPENHEMS_BRANCH', 'main')
		tmpDir = Path(os.environ.get('tmpDir', '/tmp'))
		projectName = "openhems-sample"
		myupdater = Updater(projectName, path, tmpDir=tmpDir, user=user, branch=branch)
		# myupdater.addSubmodule("emhass", "lib/emhass", maintainer="davidusb-geek")
		return myupdater

	def __init__(self, projectName, path, *, tmpDir:Path="/tmp", user="root", branch="main",
			maintainer='abriotde', subprojects=None):
		"""
		If len(branch)>20 we consider it as gitcommit id
		"""
		self.projectName = projectName
		self.path = path
		if not tmpDir.exists():
			os.mkdir(tmpDir)
		self.tmpDir = tmpDir / "autoupdate"
		if not self.tmpDir.exists():
			os.mkdir(self.tmpDir)
		os.chdir(self.tmpDir)
		self.user = user
		self.branch = branch
		self.maintainer = maintainer
		self.subprojects = subprojects
		self.gitHost = "github"

	def getRawUrl(self, path):
		"""
		Return url to get raw file.
		"""
		url = ""
		if self.gitHost=="github":
			url="https://raw.githubusercontent.com/" \
				+ self.maintainer+"/"+self.projectName+"/"+self.branch+"/"+path
		else:
			print("ERROR : unknown git host : ", self.gitHost
				,". Only 'github' is supported.")
			sys.exit(1)
		return url

	def updateFromGitClone(self):
		"""
		Git clone in order to get sources.
		"""
		tmpRepo = self.tmpDir / self.projectName
		if not tmpRepo.is_dir():
			url = self.getGitUrl()
			print("INFO : Clone ",url," on ",self.tmpDir)
			git.Repo.clone_from(url, tmpRepo)
			repo = git.Repo(tmpRepo)
		else:
			repo = git.Repo(tmpRepo)
			print("INFO : Update git repository ",repo.remotes.origin.url," on ",tmpRepo)
			repo.remotes.origin.pull()
		repo.refs.main.checkout()
		for submodule in repo.submodules:
			sdir = tmpRepo / submodule.path
			if not sdir.is_dir():
				sdir.mkdir()
			print("INFO Update ",repr(submodule))
			submodule.update(init=True, force=True)
			submodule.module().heads.master.checkout(force=True)
		self.copyOnProdExcept(tmpRepo)


	def addSubmodule(self, projectName, relativPath, *, tmpDir=None, user="root",
			branch="main", maintainer=None, subprojects=None):
		"""
		Add a git submodule.
		"""
		# TODO : find in git submodules and path and branches
		if maintainer is None:
			maintainer = self.maintainer
		if tmpDir is None:
			tmpDir = self.tmpDir / projectName
		path = self.path + "/" + relativPath
		submodule = Updater(projectName, path, tmpDir=tmpDir, user=user, branch=branch
			, maintainer=maintainer, subprojects=subprojects)
		if self.subprojects is None:
			self.subprojects = []
		self.subprojects.append(submodule)

	def getGitUrl(self):
		"""
		Return url for git clone of wall project.
		"""
		if self.gitHost=="github":
			return "https://github.com/"+self.maintainer+"/"+self.projectName+".git"
		return ""

	def getZipUrl(self):
		"""
		Return url to get git sources as zip.
		"""
		isGitCommitId = gitCommitIdRegexp.match(self.branch)
		if self.gitHost=="github":
			suburl = self.branch if isGitCommitId else ("refs/heads/"+self.branch)
			url = "https://codeload.github.com/"\
				+self.maintainer+"/"+self.projectName+"/zip/"+suburl
		else:
			print("ERROR : unknown git host : ", self.gitHost
				,". Only 'github' is supported.")
			sys.exit(1)
		return url

	def postupdate(self, startingVersion, currentVersion):
		"""
		Run specific script to updates things between 2 versions.
		"""
		# print("postupdate(",startingVersion,", ",currentVersion,")")
		if startingVersion==currentVersion:
			return False
		postupdatePath = self.path+"/scripts/postupdate/"
		versions = []
		if not os.path.exists(postupdatePath):
			return True
		for f in os.listdir(postupdatePath):
			match = postupdateScriptRegexp.match(f)
			if os.path.isfile(postupdatePath+"/"+f) and match:
				versions.append(match["version"])
			else:
				print("Skip:",f)
		cmp_items_py3 = functools.cmp_to_key(cmpVersions)
		versions.sort(key=cmp_items_py3)
		inside = False
		for version in versions:
			if not inside:
				if cmpVersions(startingVersion, version)<0:
					inside=True
			else:
				if cmpVersions(version, currentVersion)>0:
					return True
			if inside:
				print("> Run postupdate ",version)
				modName = "postupdate-"+version
				filepath = self.path+"/scripts/postupdate/"
				# https://betterstack.com/community/questions/how-to-import-python-module-dynamically/
				spec = importlib.util.spec_from_file_location(modName, filepath)
				module = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(module)
				module.update()
		return True

	def updateFromExtract(self):
		"""
		Download and extract new version
		"""
		zipfile = self.tmpDir / (self.projectName+"-"+self.branch+".zip")
		if os.path.exists(zipfile):
			os.remove(zipfile)
		url = self.getZipUrl()
		print("Download ", url)
		res = requests.get(url, timeout=30)
		with zipfile.open('wb') as fd:
			fd.write(res.content)
			with ZipFile(zipfile, 'r') as zf:
				print("Extract ", zipfile)
				zf.extractall(self.tmpDir)
				zf.close()
				return self.copyOnProdFromFileList(
					self.tmpDir / (self.projectName+"-"+self.branch)
				)
		return False

	def copyOnProdFromFileList(self, tmpPath):
		"""
		Copy on prod a limited filelist.
		"""
		print("Copy on prod ", tmpPath, " => ", self.path)
		path =  tmpPath / 'scripts/files.lst'
		with path.open('r', encoding="utf-8") as exeList:
			for file in exeList.readlines():
				filepath = tmpPath / (file.strip())
				if filepath.is_file():
					print("chmod 755 ", filepath)
					filepath.chmod(0o755)
				else:
					print("ERROR : chmod 755 ", filepath)
		for subdir in ["src","scripts", "version", "docs", "tests", "pyproject.toml"]:
			spath = tmpPath / subdir
			print(" - ",str(spath))
			if spath.is_dir():
				ok = os.system('rsync -apzh "'+str(spath)+'" "'+str(self.path)+'/"')
			else:
				ok = os.system('rsync -pzh "'+str(spath)+'" "'+str(self.path)+'/"')
			if ok!=0:
				print("ERROR : OpenHEMS/Update : Fail copy directory '"+subdir+"'")
				return False
		if self.subprojects is not None:
			self.subprojects.update()
		return True

	def copyOnProdDirExcept(self, tmpPath, relativPath=None):
		"""
		Copy on prod folder directory except some know files (.git)
		"""
		print("Copy on prod repository ",tmpPath," / ",relativPath)
		if relativPath is None:
			relativPath = Path('.')
		origin = tmpPath / relativPath
		destination = self.path / relativPath
		if not destination.is_dir():
			os.mkdir(destination)
		for file in os.listdir(origin):
			if file not in ['.', '..', 'config']  and not file.find('.git'):
				src = origin / file
				if src.is_dir():
					self.copyOnProdDirExcept(tmpPath, relativPath / file)
				else:
					self.copyOnProdFile(tmpPath, relativPath / file)

	def copyOnProdFile(self, tmpPath, relativPath):
		"""
		Copy on prod a single file
		"""
		print("Copy on prod file ",tmpPath," / ",relativPath)
		os.rename(tmpPath / relativPath, self.path / relativPath)

	def copyOnProdExcept(self, tmpPath):
		"""
		Copy on prod a directory
		"""
		self.copyOnProdDirExcept(tmpPath)
		return True

	def getCurrentVersion(self):
		"""
		Return instaled version number
		"""
		conf = ProjectConfiguration()
		return conf.getVersion()

	def getLatestVersion(self):
		"""
		Return last version number available for install
		"""
		versionUrl	= self.getRawUrl('/version')
		res = requests.get(versionUrl, timeout=30)
		# print(res," for ",versionUrl)
		if res.status_code!=200:
			return None
		return res.content.decode("utf-8").strip()

	def check4update(self):
		"""
		Check if new versions are availables.
		"""
		print("Check for new version")
		latestVersion = self.getLatestVersion()
		startingVersion = self.getCurrentVersion()
		print('Your OpenHEMS version is "'+startingVersion+'"')
		if latestVersion is None or startingVersion is None:
			print('Fail. Try later.')
			return False
		if startingVersion!=latestVersion:
			print('New version available ("'+latestVersion+'"). Updating...')
			ok = self.updateFromExtract()
			if not ok:
				print("ERROR : OpenHEMS/Update : Fail")
				return False
			currentVersion = self.getCurrentVersion()
			self.postupdate(startingVersion, currentVersion)
			self.restartOpenHEMSServer()
			print("Successfully update. Your OpenHEMS version was ",
				startingVersion," and is now ", currentVersion)
			return True
		print("No new version available. Nothing more to do.")
		return True

	def restartOpenHEMSServer(self):
		"""
		Restart OpenHEMS server.
		"""
		os.system('systemctl stop openhems.service')
		time.sleep(3)
		os.system('systemctl start openhems.service')

updater = Updater.initFromEnv()
updater.check4update()
