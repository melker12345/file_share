import struct
import socket
from crypto import decrypt_payload, encrypt_payload
import protocol

def host(port=44444):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Later set port in config.conf, maybe?
    sock.bind(('0.0.0.0', port))
    sock.listen(5)
    con, addr = sock.accept()
    return con, addr

def connect(addr, port=44444):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((addr, port))  
    return client_socket

def send_msg(sock, shared_secret,  msg_type, data):
    json_bytes = protocol.pack(msg_type, data)
    json_encrypt = encrypt_payload(shared_secret, json_bytes)
    json_msg = struct.pack('>I', len(json_encrypt))
    sock.send(json_msg + json_encrypt)

def recive_msg(sock, shared_secret):
    data = sock.recv(4)
    json_msg = struct.unpack('>I', data)[0]
    encrypted_blob = sock.recv(json_msg)
    json_decrypt = decrypt_payload(shared_secret, encrypted_blob)
    msg_type, msg_data = protocol.unpack(json_decrypt)
    return msg_type, msg_data