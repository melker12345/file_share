from cryptography.hazmat.primitives.asymmetric import x25519
import hashlib


def keygen():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def secret(my_private_key, peer_public_key):
    shared_secret = my_private_key.exchange(peer_public_key)
    return shared_secret

def code(shared_secret):
    code = hashlib.sha256(shared_secret).hexdigest()[:8]
    return code

def pubkey_to_bytes(public_key):
    return public_key.public_bytes_raw()

def bytes_to_pubkey(key_bytes):
    return x25519.X25519PublicKey.from_public_bytes(key_bytes)
