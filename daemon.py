import os
import json
import socket
import selectors
import base64

from connection import send_msg, recive_msg
from file_service import scan_env_files, read_file, write_file
from config import read_list
import protocol

IPC_HOST = "127.0.0.1"
IPC_PORT = 44445


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
        print(f"Received file saved to: {save_path}")

    elif msg_type == protocol.QUIT:
        print("Peer disconnected.")
        return False

    elif msg_type == protocol.HEARTBEAT:
        pass

    return True


def handle_cli_command(cli_conn, peer_sock, shared_secret):
    """Handle a command coming from the local CLI via the IPC socket."""
    raw = cli_conn.recv(4096)
    if not raw:
        return True

    command = json.loads(raw.decode())
    action = command.get("action")

    if action == "list":
        send_msg(peer_sock, shared_secret, protocol.LIST_REQUEST, {})
        msg_type, msg_data = recive_msg(peer_sock, shared_secret)
        cli_conn.send(json.dumps(msg_data).encode())

    elif action == "list_local":
        directories = read_list()
        files = scan_env_files(directories)
        cli_conn.send(json.dumps({"files": files}).encode())

    elif action == "request":
        path = command["path"]
        send_msg(peer_sock, shared_secret, protocol.FILE_REQUEST, {"path": path})
        msg_type, msg_data = recive_msg(peer_sock, shared_secret)
        if msg_data.get("ok"):
            content = base64.b64decode(msg_data["content"])
            save_path = command.get("save_to", path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            write_file(save_path, content)
            cli_conn.send(json.dumps({"ok": True, "saved_to": save_path}).encode())
        else:
            cli_conn.send(json.dumps({"ok": False, "error": msg_data.get("error")}).encode())

    elif action == "send":
        path = command["path"]
        content = read_file(path)
        send_msg(peer_sock, shared_secret, protocol.SEND, {
            "path": path,
            "content": base64.b64encode(content).decode(),
            "suggested_path": command.get("suggested_path", path),
        })
        cli_conn.send(json.dumps({"ok": True}).encode())

    elif action == "status":
        cli_conn.send(json.dumps({"status": "connected"}).encode())

    elif action == "dirs":
        directories = read_list()
        cli_conn.send(json.dumps({"directories": directories}).encode())

    elif action == "quit":
        send_msg(peer_sock, shared_secret, protocol.QUIT, {})
        cli_conn.send(json.dumps({"ok": True}).encode())
        return False

    return True


def run_daemon(peer_sock, shared_secret):
    """
    Main daemon loop. Listens on two things at once:
    1. The peer socket — for incoming messages from the other machine
    2. A Unix domain socket — for commands from the local CLI

    Uses `selectors` to wait on both without blocking on either.
    """
    # Create the IPC socket for local CLI communication (localhost TCP)
    ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ipc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ipc_sock.bind((IPC_HOST, IPC_PORT))
    ipc_sock.listen(1)

    sel = selectors.DefaultSelector()
    sel.register(peer_sock, selectors.EVENT_READ, data="peer")
    sel.register(ipc_sock, selectors.EVENT_READ, data="ipc_listen")

    print("Daemon running. Use 'envshare' commands to interact.")

    running = True
    while running:
        events = sel.select(timeout=None)
        for key, _ in events:

            if key.data == "peer":
                # The other machine sent us something
                running = handle_peer_message(peer_sock, shared_secret)

            elif key.data == "ipc_listen":
                # A local CLI process wants to connect
                cli_conn, _ = ipc_sock.accept()
                # Handle one command per connection, then close
                running = handle_cli_command(cli_conn, peer_sock, shared_secret)
                cli_conn.close()

    # Cleanup
    sel.unregister(peer_sock)
    sel.unregister(ipc_sock)
    sel.close()
    ipc_sock.close()
    peer_sock.close()
    print("Daemon stopped.")
