import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import socket, os
from crypto import keygen, pubkey_to_bytes, bytes_to_pubkey, secret, code

# Connecting client to server.
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('192.168.1.164', 44445))  # connect to serv

# Handles the servers pubkey 
server_pub_bytes = client.recv(1024)
print("Recived from server: ", server_pub_bytes.hex())

# Sets the clients key and sends it to server.
client_private, client_public = keygen()
client_pub_bytes = pubkey_to_bytes(client_public)
client.send(client_pub_bytes)

# Decodes the Verification code from both client and servers keys.
server_pub_key = bytes_to_pubkey(server_pub_bytes)
shared = secret(client_private, server_pub_key)
print("Verification code: ", code(shared))

# Confirmation
confirm = input("Does the code match? [y/n]: ")
if confirm == "y" or "Y" or "yes" or "Yes":
    print("Pairing successfully!")
    while True:
        cmd = input("Enter command: \n")
        if cmd in ["quit", "q", "exit"]:
            break
        client.send(cmd.encode())
        response = client.recv(4096)
        if response:
            print("Client recived: ", response.decode())


else:
    print("Pairing rejected")


print("Done!")   
