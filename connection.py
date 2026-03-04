import struct
import socket
from crypto import decrypt_payload, encrypt_payload
import protocol


def host(port=44444):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', port))
    sock.listen(5)
    con, addr = sock.accept()
    return con, addr, sock


def connect(addr, port=44444):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((addr, port))
    return client_socket


def _recv_exact(sock, n):
    """Read exactly n bytes from a socket."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def send_msg(sock, shared_secret, msg_type, data):
    json_bytes = protocol.pack(msg_type, data)
    encrypted = encrypt_payload(shared_secret, json_bytes)
    header = struct.pack('>I', len(encrypted))
    sock.sendall(header + encrypted)


def recive_msg(sock, shared_secret):
    header = _recv_exact(sock, 4)
    if not header:
        return protocol.QUIT, {}
    msg_len = struct.unpack('>I', header)[0]
    encrypted_blob = _recv_exact(sock, msg_len)
    if not encrypted_blob:
        return protocol.QUIT, {}
    decrypted = decrypt_payload(shared_secret, encrypted_blob)
    msg_type, msg_data = protocol.unpack(decrypted)
    return msg_type, msg_data
