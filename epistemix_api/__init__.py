"""
Epistemix API package - Flask app that implements the Epistemix API based on Pact contracts.
"""

__version__ = "1.0.0"
__author__ = "Zach Allen"
__email__ = "j.zachary.allen@gmail.com"

from .app import app
from .config import config

__all__ = ["app", "config"]
