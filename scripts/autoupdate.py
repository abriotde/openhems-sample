#!/usr/bin/env python3
"""
Script to update OpenHEMS installation automatically.
"""

import os
import re
import time
import functools
import importlib
from zipfile import ZipFile
import requests
from packaging.version import Version

postupdateScriptRegexp = re.compile('postupdate-(?P<version>[0-9.]*)\\.py')


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
		tmpDir = os.environ.get('tmpDir', '/tmp')
		projectName = "openhems-sample"
		return Updater(projectName, path, tmpDir=tmpDir, user=user, branch=branch)

	def __init__(self, projectName, path, *, tmpDir="/tmp", user="root", branch="main"):
		branch = "dev"
		self.projectName = projectName
		self.path = path
		self.repoRawUrl="https://raw.githubusercontent.com/abriotde/"+projectName+"/"+branch
		self.repoUrl="https://codeload.github.com/abriotde/"+projectName+"/zip/refs/heads/"+branch
		self.tmpDir = tmpDir+"/autoupdate"
		if not os.path.exists(self.tmpDir):
			os.mkdir(self.tmpDir)
		os.chdir(self.tmpDir)
		self.user = user
		self.branch = branch

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

	def update(self):
		"""
		Download and extract new version
		"""
		zipfile = self.tmpDir+"/"+self.projectName+"-"+self.branch+".zip"
		if os.path.exists(zipfile):
			os.remove(zipfile)
		res = requests.get(self.repoUrl, timeout=30)
		with open(zipfile , 'wb') as fd:
			fd.write(res.content)
		with ZipFile(zipfile, 'r') as zf:
			zf.extractall()
			zf.close()
		path = self.tmpDir+"/"+self.projectName+"-"+self.branch
		with open(path+'/scripts/files.lst', 'r', encoding="utf-8") as exeList:
			for filepath in exeList.readlines():
				os.chmod(path+"/"+(filepath.strip()), 0o755)
		for subdir in ["src","img","scripts", "version"]:
			ok = os.system('rsync -apzh --delete "'+path+"/"+subdir+'" "'+self.path+'/"')
			if ok!=0:
				print("ERROR : OpenHEMS/Update : Fail copy directory '"+subdir+"'")
				return False
		return True

	def getCurrentVersion(self):
		"""
		Return instaled version number
		"""
		with open(self.path+'/version', encoding="utf-8") as f:
			return f.read().strip()
		return None
	def getLatestVersion(self):
		"""
		Return last version number available for install
		"""
		versionUrl	= self.repoRawUrl+'/version'
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
			ok = self.update()
			if not ok:
				print("ERROR : OpenHEMS/Update : Fail")
				return False
			currentVersion = self.getCurrentVersion()
			self.postupdate(startingVersion, currentVersion)
			self.restartOpenHEMSServer()
			print("Successfully update. Your OpenHEMS version was "
				"{startingVersion} and is now {currentVersion}")
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
