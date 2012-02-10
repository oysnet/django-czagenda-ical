#!/usr/bin/env python
from setuptools import setup, find_packages

import czagenda_ical

CLASSIFIERS = [
    'Intended Audience :: Developers',    
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python'    
]

KEYWORDS = 'czagenda ical django event'


setup(name = 'czagenda ical',
    version = czagenda_ical.__version__,
    description = """Export czagenda event to ical""",
    author = czagenda_ical.__author__,
    url = "https://github.com/oxys-net/django-czagenda-ical",
    packages = find_packages(),
    classifiers = CLASSIFIERS,
    keywords = KEYWORDS,
    zip_safe = True,
    install_requires = ["oauth2>=1.5.211", "iso8601>=0.1.4"]
)