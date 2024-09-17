#!/usr/bin/env python3
import os, requests
import re, time
import functools
from importlib.machinery import SourceFileLoader


postupdateScriptRegexp = re.compile('postupdate-(?P<version>[0-9.]*)\\.py')


def cmp_versions(a, b):
	aList = a.split('.')
	bList = b.split('.')
	aLen = len(aList)
	bLen = len(bList)
	llen = max(aLen, bLen)
	for i in range(llen):
		ai = int(aList[i]) if aLen>i else 0
		bi = int(bList[i]) if bLen>i else 0
		if ai<bi:
			return -1
		elif ai>bi:
			return 1
	return 0

class Updater:
	@staticmethod
	def initFromEnv():
		path = os.environ.get('OPENHEMS_PATH')
		user = os.environ.get('OPENHEMS_USER')
		branch = os.environ.get('OPENHEMS_BRANCH')
		if branch is None: branch="main"
		tmp_dir = os.environ.get('TMP_DIR')
		project_name = "openhems-sample"
		return Updater(project_name, path, tmp_dir, user, branch)

	def __init__(self, project_name, path, tmp_dir="/tmp", user="root", branch="main"):
		branch = "dev"
		self.project_name = project_name
		self.path = path
		self.repo_raw_url="https://raw.githubusercontent.com/abriotde/"+project_name+"/"+branch
		self.repo_url="https://codeload.github.com/abriotde/"+project_name+"/zip/refs/heads/"+branch
		self.tmp_dir = tmp_dir+"/autoupdate"
		if not os.path.exists(self.tmp_dir):
			os.mkdir(self.tmp_dir)
		os.chdir(self.tmp_dir)
		self.user = user
		self.branch = branch

	def postupdate(self, starting_version, current_version):
		# print("postupdate(",starting_version,", ",current_version,")")
		if starting_version==current_version:
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
		cmp_items_py3 = functools.cmp_to_key(cmp_versions)
		versions.sort(key=cmp_items_py3)
		inside = False
		for version in versions:
			if not inside:
				if cmp_versions(starting_version, version)<0:
					inside=True
			else:
				if cmp_versions(version, current_version)>0:
					return True
			if inside:
				print("> Run postupdate ",version)
				mod_name = "postupdate-"+version
				filepath = self.path+"/scripts/postupdate/"
				pyscript= SourceFileLoader(
					mod_name,
					filepath+"/"+mod_name+".py"
				).load_module()
				pyscript.update()
		return True

	def update(self):
		zipfile = self.tmp_dir+"/"+self.project_name+"-"+self.branch+".zip"
		if os.path.exists(zipfile): os.remove(zipfile)
		res = requests.get(self.repo_url)
		open(zipfile , 'wb').write(res.content)
		from zipfile import ZipFile
		zf = ZipFile(zipfile, 'r')
		zf.extractall()
		zf.close()
		path = self.tmp_dir+"/"+self.project_name+"-"+self.branch
		exeList = open(path+'/scripts/files.lst', 'r')
		for filepath in exeList.readlines():
			os.chmod(path+"/"+(filepath.strip()), 0o755)
		for subdir in ["src","img","scripts", "version"]:
			ok = os.system('rsync -apzh --delete "'+path+"/"+subdir+'" "'+self.path+'/"')
			if ok!=0:
				print("ERROR : OpenHEMS/Update : Fail copy directory '"+subdir+"'")
				return False
		return True

	def getCurrentVersion(self):
		with open(self.path+'/version') as f:
			return f.read().strip()
		return None
	def getLatestVersion(self):
		version_url	= self.repo_raw_url+'/version'
		res = requests.get(version_url)
		# print(res," for ",version_url)
		if res.status_code!=200:
			return None
		return res.content.decode("utf-8").strip()

	def check4update(self):
		print("Check for new version")
		latest_version = self.getLatestVersion()
		starting_version = self.getCurrentVersion()
		print('Your OpenHEMS version is "'+starting_version+'"')
		if latest_version is None or starting_version is None:
			print('Fail. Try later.')
			return False
		if starting_version!=latest_version:
			print('New version available ("'+latest_version+'"). Updating...')
			ok = self.update()
			if not ok:
				print("ERROR : OpenHEMS/Update : Fail copy directory '"+subdir+"'")
				return False
			current_version = self.getCurrentVersion()
			self.postupdate(starting_version, current_version)
			self.restartOpenHEMSServer()
			print("Successfully update. Your OpenHEMS version was "+starting_version+" and is now "+current_version)
			return True
		else:
			print("No new version available. Nothing more to do.")
			return True
	def restartOpenHEMSServer(self):
		os.system('systemctl stop openhems.service')
		time.sleep(3)
		os.system('systemctl start openhems.service')

updater = Updater.initFromEnv()
updater.check4update()

