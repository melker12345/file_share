import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import socket, os
from crypto import keygen, pubkey_to_bytes, bytes_to_pubkey, secret, code

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('192.168.1.164', 44444))  # connect to serv

server_pub_bytes = client.recv(1024)
print("Recived from server: ", server_pub_bytes.hex())

client_private, client_public = keygen()
client_pub_bytes = pubkey_to_bytes(client_public)
client.send(client_pub_bytes)


server_pub_key = bytes_to_pubkey(server_pub_bytes)
shared = secret(client_private, server_pub_key)
print("Verification code: ", code(shared))



print("Done!")   
