# coding: utf-8
from setuptools import setup

setup(
    name='debug-panel',
    version='0.8.4',
    author=u'Joël Billaud',
    author_email='jbillaud@gmail.com',
    packages=['debug_panel'],
    include_package_data=True,
    url='https://github.com/ruandao/django-debug-panel',
    license='BSD',
    description='django-debug-toolbar in WebKit DevTools. Works fine with background Ajax requests and non-HTML responses',
    long_description=open('README.rst').read(),
    install_requires=[
        "django-debug-toolbar >= 1.0"
    ],
)
