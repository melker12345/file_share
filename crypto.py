from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

import os
import hashlib

def keygen():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def secret(my_private_key, peer_public_key) :
    shared_secret = my_private_key.exchange(peer_public_key)
    return shared_secret

def code(shared_secret):
    hex_val = hashlib.sha256(shared_secret).hexdigest()[:4]
    code = str(int(hex_val, 16)).zfill(4)
    return code

def pubkey_to_bytes(public_key):
    return public_key.public_bytes_raw()

def bytes_to_pubkey(key_bytes):
    return x25519.X25519PublicKey.from_public_bytes(key_bytes)

def encrypt(shared_secret, message):
    key = hashlib.sha256(shared_secret).digest()
    nonce = os.urandom(12)
    cipher = ChaCha20Poly1305(key)
    cipher_text = cipher.encrypt(nonce, message.encode(), None)
    
    return nonce + cipher_text

def decrypt(shared_secret, cipher_text):
    key = hashlib.sha256(shared_secret).digest()
    nonce = cipher_text[:12]
    cipher_text = cipher_text[12:]
    cipher = ChaCha20Poly1305(key)
    decrypted = cipher.decrypt(nonce, cipher_text, None)
    return cipher_text.decode()