from crypto import keygen, secret, code, pubkey_to_bytes, bytes_to_pubkey
from cryptography.hazmat.primitives import serialization

alice_private, alice_public = keygen()
bob_private, bob_public = keygen()


alice_pub_bytes = pubkey_to_bytes(alice_public)
bob_pub_bytes = pubkey_to_bytes(bob_public)

print("alice public key to bytes:", alice_pub_bytes.hex())
print("bob public key to bytes:", bob_pub_bytes.hex())

alice_for_bob = bytes_to_pubkey(bob_pub_bytes)
bob_for_alice = bytes_to_pubkey(alice_pub_bytes)

secret_alice = secret(alice_private, alice_for_bob)
secret_bob = secret(bob_private, bob_for_alice)

print("Alice code: ", code(secret_alice))
print("Bob code: ", code(secret_bob))
print("Match: ", code(secret_alice) == code(secret_bob))
