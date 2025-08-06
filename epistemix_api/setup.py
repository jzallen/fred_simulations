"""
Setup script for the Epistemix CLI.

This allows the CLI to be installed as a command-line tool.
"""

from setuptools import setup, find_packages

setup(
    name='epistemix-cli',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'click>=8.0.0',
        'boto3>=1.20.0',
        'sqlalchemy>=2.0.0',
        'returns>=0.20.0',
    ],
    entry_points={
        'console_scripts': [
            'epistemix=epistemix_api.cli:cli',
        ],
    },
    python_requires='>=3.10',
)