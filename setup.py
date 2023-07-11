#!/usr/bin/env python
# coding=utf-8
from io import open

from setuptools import setup

setup(
	name='xadmin',
	version='3.2.0',
	description='Drop-in replacement of Django admin comes with lots of goodies, '
	            'fully extensible with plugin support, pretty UI based on Twitter Bootstrap.',
	long_description=open('README.rst', encoding='utf-8').read(),
	author='sshwsfc',
	author_email='sshwsfc@gmail.com',
	license=open('LICENSE', encoding='utf-8').read(),
	url='https://github.com/alexsilva/django-xadmin',
	download_url='https://github.com/alexsilva/django-xadmin/archive/python3-dj32.zip',
	packages=['xadmin', 'xadmin.migrations', 'xadmin.plugins', 'xadmin.templatetags', 'xadmin.views'],
	include_package_data=True,
	install_requires=[
		'django>=3,<4',
		'django-crispy-forms==2.0',
		'django-import-export==3.0.2',
		'django-reversion==5.0.4',
		'django-formtools==2.4',
		'httplib2==0.22.0'
	],
	extras_require={
		'Excel': ['xlwt', 'xlsxwriter'],
		'Reversion': ['django-reversion>=5.0.2'],
	},
	zip_safe=False,
	keywords=['admin', 'django', 'xadmin', 'bootstrap'],
	classifiers=[
		'Development Status :: 5 - Beta',
		'Environment :: Web Environment',
		'Framework :: Django',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: BSD License',
		'Operating System :: OS Independent',
		"Programming Language :: JavaScript",
		'Programming Language :: Python',
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.9",
		"Topic :: Internet :: WWW/HTTP",
		"Topic :: Internet :: WWW/HTTP :: Dynamic Content",
		"Topic :: Software Development :: Libraries :: Python Modules",
	]
)
