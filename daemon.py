import os
import struct
import json
import socket
import selectors
import base64

from connection import send_msg, recive_msg
from file_service import scan_env_files, read_file, write_file
from config import read_list, PID_FILE
from peers import find_peer, get_shared_secret
import protocol

IPC_HOST = "127.0.0.1"
IPC_PORT = 44445


def ipc_send(sock, data):
    """Send a length-prefixed JSON message over the IPC socket."""
    payload = json.dumps(data).encode()
    sock.sendall(struct.pack('>I', len(payload)) + payload)


def ipc_recv(sock):
    """Receive a length-prefixed JSON message from the IPC socket."""
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        return None
    msg_len = struct.unpack('>I', raw_len)[0]
    raw_msg = _recv_exact(sock, msg_len)
    if not raw_msg:
        return None
    return json.loads(raw_msg.decode())


def _recv_exact(sock, n):
    """Read exactly n bytes from a socket."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def handle_peer_message(peer_sock, shared_secret):
    """Handle an incoming message from the connected peer."""
    msg_type, msg_data = recive_msg(peer_sock, shared_secret)

    if msg_type == protocol.LIST_REQUEST:
        directories = read_list()
        files = scan_env_files(directories)
        send_msg(peer_sock, shared_secret, protocol.LIST_RESPONSE, {"files": files})

    elif msg_type == protocol.FILE_REQUEST:
        path = msg_data["path"]
        try:
            content = read_file(path)
            send_msg(peer_sock, shared_secret, protocol.FILE_RESPONSE, {
                "path": path,
                "content": base64.b64encode(content).decode(),
                "ok": True,
            })
        except Exception as e:
            send_msg(peer_sock, shared_secret, protocol.FILE_RESPONSE, {
                "ok": False,
                "error": str(e),
            })

    elif msg_type == protocol.SEND:
        content = base64.b64decode(msg_data["content"])
        save_path = msg_data.get("suggested_path", msg_data["path"])
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        write_file(save_path, content)

    elif msg_type == protocol.QUIT:
        return False

    elif msg_type == protocol.HEARTBEAT:
        pass

    return True


def handle_cli_command(cli_conn, peer_sock, shared_secret):
    """Handle a command coming from the local CLI via the IPC socket."""
    command = ipc_recv(cli_conn)
    if not command:
        return True, False

    action = command.get("action")

    if action == "list":
        send_msg(peer_sock, shared_secret, protocol.LIST_REQUEST, {})
        msg_type, msg_data = recive_msg(peer_sock, shared_secret)
        ipc_send(cli_conn, msg_data)

    elif action == "list_local":
        directories = read_list()
        files = scan_env_files(directories)
        ipc_send(cli_conn, {"files": files})

    elif action == "request":
        path = command["path"]
        send_msg(peer_sock, shared_secret, protocol.FILE_REQUEST, {"path": path})
        msg_type, msg_data = recive_msg(peer_sock, shared_secret)
        if msg_data.get("ok"):
            content = base64.b64decode(msg_data["content"])
            save_path = command.get("save_to", path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            write_file(save_path, content)
            ipc_send(cli_conn, {"ok": True, "saved_to": save_path})
        else:
            ipc_send(cli_conn, {"ok": False, "error": msg_data.get("error")})

    elif action == "send":
        path = command["path"]
        content = read_file(path)
        send_msg(peer_sock, shared_secret, protocol.SEND, {
            "path": path,
            "content": base64.b64encode(content).decode(),
            "suggested_path": command.get("suggested_path", path),
        })
        ipc_send(cli_conn, {"ok": True})

    elif action == "status":
        ipc_send(cli_conn, {"status": "connected"})

    elif action == "dirs":
        directories = read_list()
        ipc_send(cli_conn, {"directories": directories})

    elif action == "quit":
        send_msg(peer_sock, shared_secret, protocol.QUIT, {})
        ipc_send(cli_conn, {"ok": True})
        return True, True

    return True, False


def run_daemon(peer_sock, shared_secret, listen_sock=None):
    """
    Main daemon loop. Listens on two things at once:
    1. The peer socket -- for incoming messages from the other machine
    2. A localhost TCP socket -- for commands from the local CLI

    If listen_sock is provided (host mode), the daemon will wait for
    reconnections from known peers when the current peer disconnects.
    """
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ipc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ipc_sock.bind((IPC_HOST, IPC_PORT))
    ipc_sock.listen(5)

    sel = selectors.DefaultSelector()
    sel.register(peer_sock, selectors.EVENT_READ, data="peer")
    sel.register(ipc_sock, selectors.EVENT_READ, data="ipc_listen")
    if listen_sock:
        sel.register(listen_sock, selectors.EVENT_READ, data="host_listen")

    shutdown = False
    while not shutdown:
        try:
            events = sel.select(timeout=None)
            for key, _ in events:
                if key.data == "peer":
                    alive = handle_peer_message(peer_sock, shared_secret)
                    if not alive:
                        sel.unregister(peer_sock)
                        peer_sock.close()
                        peer_sock = None
                        if not listen_sock:
                            shutdown = True

                elif key.data == "ipc_listen":
                    cli_conn, _ = ipc_sock.accept()
                    if peer_sock:
                        ok, quit_requested = handle_cli_command(cli_conn, peer_sock, shared_secret)
                        if quit_requested:
                            shutdown = True
                    else:
                        ipc_send(cli_conn, {"error": "No peer connected. Waiting for reconnection."})
                    cli_conn.close()

                elif key.data == "host_listen":
                    new_conn, addr = listen_sock.accept()
                    peer_ip = addr[0]
                    saved = find_peer(peer_ip)
                    if saved:
                        if peer_sock:
                            sel.unregister(peer_sock)
                            peer_sock.close()
                        peer_sock = new_conn
                        shared_secret = get_shared_secret(saved)
                        sel.register(peer_sock, selectors.EVENT_READ, data="peer")
                    else:
                        new_conn.close()

        except Exception:
            shutdown = True

    # Cleanup
    if peer_sock:
        try:
            sel.unregister(peer_sock)
        except Exception:
            pass
        peer_sock.close()
    sel.unregister(ipc_sock)
    if listen_sock:
        sel.unregister(listen_sock)
        listen_sock.close()
    sel.close()
    ipc_sock.close()
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
