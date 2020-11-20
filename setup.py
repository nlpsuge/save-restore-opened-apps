"""
See: https://github.com/pypa/sampleproject/blob/master/setup.py
"""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    # pip install xsession-manager
    name='xsession-manager',
    version='1.0.0',
    description='A command line to save and restore sessions for X11 desktops like Gnome, with many other features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/nlpsuge/xsession-manager',
    author='nlpsuge',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Management :: Session Manager :: X Session',
        'License :: GNU General Public License v3.0',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='manager, X.org, session, save and restore',
    packages=find_packages(include=['xsession_manager', 'xsession_manager.*']),
    python_requires='>=3',

    install_requires=[
        'psutil>=5.7.2',
        'pycurl>=7.43.0.5',
    ],

    entry_points={  # Optional
        'console_scripts': [
            'xsession-manager = xsession_manager.main:run',
            'xsm = xsession_manager.main:run',
        ],
    },

    project_urls={
        'Bug Reports': 'https://github.com/nlpsuge/xsession-manager/issues',
        'Source': 'https://github.com/nlpsuge/xsession-manager',
    },
)
