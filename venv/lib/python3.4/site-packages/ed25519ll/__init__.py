# -*- coding: utf-8 -*-

import warnings
import os
import os.path
import pkg_resources
from collections import namedtuple
from distutils import sysconfig
from distutils.util import get_platform
import ctypes
from ctypes import c_char_p, c_ulonglong, POINTER, byref

__all__ = ['crypto_sign', 'crypto_sign_open', 'crypto_sign_keypair', 'Keypair',
           'PUBLICKEYBYTES', 'SECRETKEYBYTES', 'SIGNATUREBYTES']

PUBLICKEYBYTES=32
SECRETKEYBYTES=64
SIGNATUREBYTES=64

Keypair = namedtuple('Keypair', ('vk', 'sk')) # verifying key, secret key

try:
    from ed25519ll.ed25519ct import (crypto_sign_keypair, 
                                     crypto_sign,
                                     crypto_sign_open)
except ImportError: # pragma no cover
    from ed25519ll.ed25519py import (crypto_sign_keypair,
                                     crypto_sign,
                                     crypto_sign_open)
