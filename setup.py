"""A setuptools based setup module for epaper."""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='epaper',
    version='0.1.0.dev1',
    description='A Simple Scraper and Viewer Application for The Times of India E-Newspaper',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/rpdeo/times-epaper',
    author='Dr. Rajesh P. Deo',
    author_email='rajesh.deo@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: Linux',
        'Environment :: MacOS X',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        'Topic :: Multimedia :: Graphics :: Viewers',
        'Topic :: Office/Business :: News/Diary',
        'Topic :: Utilities',
    ],
    keywords='news scraper image-viewer app cross-platform gui',
    packages=find_packages(
        exclude=['contrib', 'docs', 'tests', 'logs']),
    install_requires=[ 
        'requests',
        'beautifulsoup4',
        'bs4',
        'Pillow',
        'toga',
        'click',
        'prompt_toolkit',
    ],
    extras_require={
        'dev': [
            'check-manifest',
        ],
        'test': [
            'coverage',
            'pytest',
            'tox',
        ],
    },
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'epaper=epaper.cli:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/rpdeo/times-epaper/issues',
        'Source': 'https://github.com/rpdeo/times-epaper',
    },
)
