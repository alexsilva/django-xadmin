#!/usr/bin/env python
from io import open

from setuptools import setup

# version_tuple = __import__('xadmin').VERSION
# version = ".".join([str(v) for v in version_tuple])

setup(
	name='xadmin',
	version='3.0.0',
	description='Drop-in replacement of Django admin comes with lots of goodies, fully extensible with plugin support, pretty UI based on Twitter Bootstrap.',
	long_description=open('README.rst', encoding='utf-8').read(),
	author='sshwsfc',
	author_email='sshwsfc@gmail.com',
	license=open('LICENSE', encoding='utf-8').read(),
	url='http://www.xadmin.io',
	download_url='http://github.com/sshwsfc/django-xadmin/archive/master.zip',
	packages=['xadmin', 'xadmin.migrations', 'xadmin.plugins', 'xadmin.templatetags', 'xadmin.views'],
	include_package_data=True,
	install_requires=[
		'django>=3,<4',
		'django-crispy-forms==1.14.0',
		'django-import-export==2.8.0',
		'django-reversion==5.0.2',
		'django-formtools==2.4',
		'httplib2==0.20.4'
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
		"Programming Language :: Python :: 3.7",
		"Topic :: Internet :: WWW/HTTP",
		"Topic :: Internet :: WWW/HTTP :: Dynamic Content",
		"Topic :: Software Development :: Libraries :: Python Modules",
	]
)
