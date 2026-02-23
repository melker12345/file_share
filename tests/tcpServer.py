import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import socket, os
from crypto import keygen, pubkey_to_bytes, secret, code, bytes_to_pubkey

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('192.168.1.164', 44444))
sock.listen(5)

con, addr = sock.accept()

server_private, server_public = keygen()
server_pub_bytes = pubkey_to_bytes(server_public)
con.send(server_pub_bytes)

server_pub_bytes = con.recv(1024)
print("Recived from client: ",server_pub_bytes.hex())

client_pub_key = bytes_to_pubkey(server_pub_bytes)
shared = secret(server_private, client_pub_key)
print("Verification code: ", code(shared))


print("Done!")
