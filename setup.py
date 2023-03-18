#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages

setup(name='Bing Chat Discord Bot',
      version='1.0',
      description='A discord bot to use Bing Chat',
      author='Yang Liu',
      author_email='yang.jace.liu@linux.com',
      url='https://github.com/yang-jace-liu/bing-chat-bot',
      scripts=['scripts/bing-chat-bot'],
      packages=find_packages(),
     )
