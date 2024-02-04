from setuptools import setup, find_packages

VERSION = '0.1.1'
DESCRIPTION = 'Package for simplify classes and objects transfer over network'

with open('README.md', 'r') as f:
    desc = f.read()

LONG_DESCRIPTION = desc

setup(
    name="oon",
    version=VERSION,
    author="Ivashka (Ivan Rakov)",
    author_email="<ivashka.2.r@gmail.com>",
    description=DESCRIPTION,
    packages=find_packages(),
    install_requires=[],
    keywords=['python', 'network', 'sockets', 'objects', 'classes', 'oon'],
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    platforms='any',
)
