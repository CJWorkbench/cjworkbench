# -*- coding: utf-8 -*-

from nose.tools import raises
import ed25519ll.ed25519ct, ed25519ll.ed25519py

def test_ed25519ll():
    for impl in ed25519ll.ed25519ct, ed25519ll.ed25519py:
        inner_ed25519ll(impl)

def inner_ed25519ll(ed25519ll):
    msg = b"The rain in Spain stays mainly on the plain"
    kp = ed25519ll.crypto_sign_keypair()
    signed = ed25519ll.crypto_sign(msg, kp.sk)    
    
    @raises(ValueError)
    def open_corrupt(): 
        corrupt = signed[ed25519ll.SIGNATUREBYTES:] + b'U' + signed[ed25519ll.SIGNATUREBYTES+1:]
        ed25519ll.crypto_sign_open(corrupt, kp.vk)                
    open_corrupt()
    
    @raises(ValueError)
    def short_sk():
        signed = ed25519ll.crypto_sign(msg, kp.sk[:-1])
    short_sk()
    
    @raises(ValueError)
    def short_vk(): 
        corrupt = signed[ed25519ll.SIGNATUREBYTES:] + b'U' + signed[ed25519ll.SIGNATUREBYTES+1:]
        ed25519ll.crypto_sign_open(corrupt, kp.vk[:-1])                
    short_vk()
    
    ed25519ll.crypto_sign_open(signed, kp.vk)

def test_cover_warn_seed():
    for impl in ed25519ll.ed25519ct, ed25519ll.ed25519py:
        inner_cover_warn_seed(impl)
            
def inner_cover_warn_seed(ed25519ll):
    ed25519ll.crypto_sign_keypair(b'*'*32)
    
@raises(ValueError)
def test_bad_seed_size():
    for impl in ed25519ll.ed25519ct, ed25519ll.ed25519py:
        inner_bad_seed_size(impl)

def inner_bad_seed_size(ed25519ll):
    ed25519ll.crypto_sign_keypair(b'*'*31)

if __name__ == "__main__":
    test_ed25519ll()
