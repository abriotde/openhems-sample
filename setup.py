"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "readme.md").read_text(encoding="utf-8")

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/abriotde/openhems-sample.git",
	author="OpenHomeSystem",
	author_email="contact@openhomesystem.com",
	# For a list of valid classifiers, see https://pypi.org/classifiers/
	package_dir={"": "src"},
	packages=find_packages(where="src"),
	python_requires=">=3.8, <4",
	# install_requires=["requests", "pandas", "pyyaml", "pyramid", "pyramid-jinja2"],
	extras_require={
		# "dev": ["check-manifest"],
		# "test": ["coverage"],
	},
	package_data={
	# 	"sample": ["package_data.dat"],
	},
)
