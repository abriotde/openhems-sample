#!/bin/env python3
"""
Script used to test pylint compliance of this project and correct it.
"""
import os
import re
import json
from pathlib import Path

pattern_line = re.compile(r"^(.*):([0-9]+):([0-9]+): ([A-Z][0-9][0-9][0-9][0-9]): (.*)")
snake_case_descr = re.compile(r'.*name "(.*)".* conform to snake_case naming style.*')
snake_case_transformer = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

snake_case_conversion_todo = {}
snake_case_conversion = {}
SNAKECASE_CONVERSION_FILE = 'pylint_snake_case_conversion.json'

def convert2CamelcaseFile(file, word, snakeCaseWord):
	"""
	Should be used to convert a file to camelcase: CANCELED
	"""
	update = False
	with re.compile("(.*[ (,\",'.])("+word+")([ (,\",'].*)") as regex:
		filecontent = ""
		with open(file, 'r', encoding='utf-8') as fd:
			for line in fd:
				ok = regex.match(line)
				if ok:
					update = True
					newLine = ok[1]+snakeCaseWord+ok[3]
					print("Find '",word,"' in '",file, \
						"' (\n",line,"\n => \n",newLine,"\n)")
					filecontent+=newLine
				else:
					filecontent+=line
			if update:
				with open(file, 'w', encoding='utf-8') as f:
					f.write(filecontent)
	return update

def convert2camelcase(word, snakeCaseWord):
	"""
	Should be used to convert a specific word to camelcase in all folders: CANCELED
	"""
	# TODO ?
	convert2CamelcaseFile("src/openhems/main.py", word, snakeCaseWord)

def analyzeFolder(folder):
	"""
	Analyze with "pylint" all python gited files
	"""
	stream = os.popen('pylint $(git ls-files \''+str(folder)+'*.py\')')
	for line in stream.readlines():
		print(line)
		# pylint: disable=pointless-string-statement
		"""
		ok = pattern_line.match(line)
		if ok:
			file = ok[1]
			linenb = ok[2]
			# charstart = ok[3]
			code = ok[4]
			description = ok[5]
			# print(code, file, linenb)
			if code=="C0103": # Variable name "aList" doesn't conform to snake_case naming style
				# print(file, code, description)
				ok = snake_case_descr.match(description)
				if ok:
					word = ok[1]
					if not word in snake_case_conversion:
						snakeCaseWord = snake_case_transformer.sub('_', word).lower()
						snake_case_conversion_todo[word] = snakeCaseWord
						print(word,"=>",snakeCaseWord)
					else:
						snakeCaseWord = snake_case_conversion[word]
						print("File:",file,"; Line:",linenb," : ", word,"=>",snakeCaseWord)
						# convert2camelcase(word, snakeCaseWord)
				# else: print("ERROR: should be a snake_case prolem: ", description)
			elif code=="W0511":
				# It's for TODO code (fixme).
				pass
			else:
				print(line)
		else:
			print(line)
		"""

def initSnakeCaseConversion():
	"""
	Initialyze the script
	"""
	if os.path.isfile(SNAKECASE_CONVERSION_FILE):
		with open(SNAKECASE_CONVERSION_FILE, 'r', encoding="utf-8") as f:
			return json.load(f)
	return {}

def finalyze():
	"""
	Finalyze the script
	"""
	if len(snake_case_conversion_todo)>0:
		print(snake_case_conversion_todo)
		snake_case_conversion.update(snake_case_conversion_todo)
		with open(SNAKECASE_CONVERSION_FILE, 'w', encoding="utf-8") as f:
			f.write(json.dumps(snake_case_conversion, indent=2))

# snake_case_conversion = initSnakeCaseConversion()

ROOT_PATH = Path(__file__).parents[1]
analyzeFolder(ROOT_PATH / "src/openhems")
analyzeFolder(ROOT_PATH/"scripts")
analyzeFolder(ROOT_PATH/"tests")
