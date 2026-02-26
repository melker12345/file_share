from crypto import keygen, pubkey_to_bytes, secret, code, bytes_to_pubkey


def pairing_host(sock):
    server_private, server_public = keygen()
    server_pub_bytes = pubkey_to_bytes(server_public)
    sock.send(server_pub_bytes)

    # listens for clients code.
    client_pub_bytes = sock.recv(1024)
    client_pub_key = bytes_to_pubkey(client_pub_bytes)
    shared = secret(server_private, client_pub_key)
    if confirm_con(shared):
        return shared
    else:
        return None

def pairing_client(sock):
    server_pub_bytes = sock.recv(1024)
    # Sets the clients key and sends it to server.
    client_private, client_public = keygen()
    client_pub_bytes = pubkey_to_bytes(client_public)
    sock.send(client_pub_bytes)

    # Decodes the Verification code from both client and servers keys.
    server_pub_key = bytes_to_pubkey(server_pub_bytes)
    shared = secret(client_private, server_pub_key)
    if confirm_con(shared):
        return shared
    else:
        return None

def confirm_con(shared):
    # Confirmation
    print("Verification code: ", code(shared))
    confirm = input("Does the code match? [y/n]: ")
    if confirm.lower() in ["y", "yes"]:
        print("Paring success!")
        return True

    else:
        print("Pairing rejected")
        return False