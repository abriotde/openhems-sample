"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "readme.md").read_text(encoding="utf-8")

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
	name="openhems",
	version="0.1.0",
	description="A sample Home Energy Managment System based on Home-Assistant",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/pypa/sampleproject",
	author="OpenHomeSystem",
	author_email="contact@openhomesystem.com",
	# For a list of valid classifiers, see https://pypi.org/classifiers/
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Intended Audience :: Developers",
		"Topic :: Software Development :: Build Tools",
		"License :: GPL-3.0-or-later",
		"Programming Language :: Python :: 3 :: Only",
	],
	keywords="energy, HEMS, home automation, home-assistant",
	package_dir={"": "src"},
	packages=find_packages(where="src"),
	python_requires=">=3.8, <4",
	install_requires=["pandas", "pyyaml", "pyramid", "pyramid-jinja2"],
	extras_require={
		# "dev": ["check-manifest"],
		# "test": ["coverage"],
	},
	package_data={
	# 	"sample": ["package_data.dat"],
	},
	# Entry points. The following would provide a command called `sample` which
	# executes the function `main` from this package when invoked:
	entry_points={
		"console_scripts": [
			"openhems=openhems:main",
		],
	},
	project_urls={  # Optional
		"Home Page": "https://openhomesystem.com",
		"Source": "https://github.com/abriotde/openhems-sample",
		"Bug Reports": "https://github.com/abriotde/openhems-sample/issues",
	#	"Funding": "https://donate.pypi.org",
	#	"Say Thanks!": "http://saythanks.io/to/example",
	},
)
