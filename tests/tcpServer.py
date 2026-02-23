import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import socket, os
from crypto import keygen, pubkey_to_bytes, secret, code, bytes_to_pubkey

# Start server and listen
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('192.168.1.164', 44445))
sock.listen(5)
con, addr = sock.accept()

# Sets up the servers keys and send
server_private, server_public = keygen()
server_pub_bytes = pubkey_to_bytes(server_public)
con.send(server_pub_bytes)

# listens for clients code.
client_pub_bytes = con.recv(1024)
print("Recived from client: ", client_pub_bytes.hex())

client_pub_key = bytes_to_pubkey(client_pub_bytes)
shared = secret(server_private, client_pub_key)
print("Verification code: ", code(shared))


# Confirmation
confirm = input("Does the code match? [y/n]: ")

if confirm == "y" or "Y" or "yes" or "Yes":
    print("Pairing successfully!")
    while True:
        cmd = input("Enter command: \n")
        if cmd in ["quit", "q", "exit"]:
            break

        con.send(cmd.encode())
        response = con.recv(4096)
        if response:
            print("Server recived: ", response.decode())
else:
    print("Pairing rejected")



print("Done!")
