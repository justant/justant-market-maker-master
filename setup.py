#!/usr/bin/env python
from setuptools import setup
from os.path import dirname, join

import market_maker


here = dirname(__file__)


setup(name='bitmex-market-maker',
      version=market_maker.__version__,
      description='Just bot for BitMEX API',
      url='https://github.com/BitMEX/sample-market-maker',
      long_description=open(join(here, 'README.md')).read(),
      long_description_content_type='text/markdown',
      author='Justant Seo',
      author_email='suhday@naver.com',
      install_requires=[
          'requests',
          'websocket-client',
          'future'
      ],
      packages=['market_maker', 'market_maker.auth', 'market_maker.order', 'market_maker.plot', 'market_maker.utils', 'market_maker.ws', 'log', 'client_api'],
      entry_points={
          'console_scripts': ['marketmaker = custom_strategy:run']
      }
      )
