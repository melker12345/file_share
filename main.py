import argparse
import json
import os
import socket
import struct
import sys
import time

from connection import host, connect
from pairing import pairing_host, pairing_client
from daemon import run_daemon, IPC_HOST, IPC_PORT
from config import add_path, PID_FILE, RECEIVED_DIR, LOG_FILE
from peers import save_peer, load_peers, find_peer, get_shared_secret, forget_peer


def _ipc_send(sock, data):
    payload = json.dumps(data).encode()
    sock.sendall(struct.pack('>I', len(payload)) + payload)


def _ipc_recv(sock):
    raw_len = b""
    while len(raw_len) < 4:
        chunk = sock.recv(4 - len(raw_len))
        if not chunk:
            return None
        raw_len += chunk
    msg_len = struct.unpack('>I', raw_len)[0]
    raw_msg = b""
    while len(raw_msg) < msg_len:
        chunk = sock.recv(msg_len - len(raw_msg))
        if not chunk:
            return None
        raw_msg += chunk
    return json.loads(raw_msg.decode())


def daemon_is_running():
    if not os.path.exists(PID_FILE):
        return False
    with open(PID_FILE, "r") as f:
        try:
            pid = int(f.read().strip())
        except ValueError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        os.remove(PID_FILE)
        return False


def send_to_daemon(command):
    """Connect to the running daemon via local TCP, send a command, return the response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((IPC_HOST, IPC_PORT))
        _ipc_send(sock, command)
        response = _ipc_recv(sock)
        sock.close()
        if response is None:
            print("No response from daemon. The peer may have disconnected.")
            return {"error": "No response from daemon"}
        return response
    except ConnectionRefusedError:
        print("Daemon is not running. Start with 'envshare host' or 'envshare connect <ip>' first.")
        sys.exit(1)


def daemonize(peer_sock, shared_secret, listen_sock=None):
    """Fork the daemon to the background. Parent returns, child runs daemon loop."""
    pid = os.fork()
    if pid > 0:
        print(f"Daemon running in background (PID: {pid})")
        return
    os.setsid()
    log_fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(devnull)
    os.close(log_fd)
    run_daemon(peer_sock, shared_secret, listen_sock=listen_sock)
    os._exit(0)


def auto_start_daemon():
    """If daemon is not running but we have a saved peer, reconnect in background."""
    if daemon_is_running():
        return True

    peers = load_peers()
    if not peers:
        print("No known peers. Run 'envshare host' or 'envshare connect <ip>' first.")
        return False

    peer = peers[0]
    ip = peer["ip"]
    port = peer["port"]
    shared_secret = get_shared_secret(peer)

    print(f"Reconnecting to {ip}:{port}...")
    try:
        sock = connect(ip, port=port)
    except (ConnectionRefusedError, OSError) as e:
        print(f"Could not connect to {ip}:{port}: {e}")
        return False

    daemonize(sock, shared_secret)
    time.sleep(0.5)
    return True


def ensure_daemon():
    """Make sure the daemon is running before sending a command."""
    if daemon_is_running():
        return True
    return auto_start_daemon()


def cmd_host(args):
    if daemon_is_running():
        print("Daemon is already running.")
        return

    print(f"Listening on port {args.port}...")
    con, addr, listen_sock = host(port=args.port)
    print(f"Connected to {addr[0]}")

    shared_secret = pairing_host(con)
    if shared_secret is None:
        print("Pairing rejected. Closing connection.")
        con.close()
        listen_sock.close()
        return

    save_peer(addr[0], args.port, shared_secret)
    daemonize(con, shared_secret, listen_sock=listen_sock)


def cmd_connect(args):
    if daemon_is_running():
        print("Daemon is already running.")
        return

    port = args.port
    saved = find_peer(args.address, port)

    if saved:
        print(f"Reconnecting to known peer {args.address}:{port}...")
        shared_secret = get_shared_secret(saved)
        try:
            sock = connect(args.address, port=port)
        except (ConnectionRefusedError, OSError) as e:
            print(f"Could not connect: {e}")
            return
        save_peer(args.address, port, shared_secret)
        daemonize(sock, shared_secret)
    else:
        print(f"Connecting to {args.address}:{port}...")
        try:
            sock = connect(args.address, port=port)
        except (ConnectionRefusedError, OSError) as e:
            print(f"Could not connect: {e}")
            return
        print("Connected!")

        shared_secret = pairing_client(sock)
        if shared_secret is None:
            print("Pairing rejected. Closing connection.")
            sock.close()
            return

        save_peer(args.address, port, shared_secret)
        daemonize(sock, shared_secret)


def cmd_list(args):
    if not ensure_daemon():
        return
    if args.local:
        result = send_to_daemon({"action": "list_local"})
    else:
        result = send_to_daemon({"action": "list"})

    files = result.get("files", [])
    if not files:
        print("No .env files found.")
        return

    label = "Local" if args.local else "Remote"
    print(f"\n{label} .env files:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f['path']}  ({f['project']}, {f['size']} bytes)")
    print()


def cmd_request(args):
    if not ensure_daemon():
        return
    command = {"action": "request", "path": args.path}
    if args.save_to:
        command["save_to"] = args.save_to
    else:
        remote_path = args.path
        project = os.path.basename(os.path.dirname(remote_path))
        filename = os.path.basename(remote_path)
        command["save_to"] = os.path.join(RECEIVED_DIR, project, filename)

    result = send_to_daemon(command)
    if result.get("ok"):
        print(f"File received and saved to: {result['saved_to']}")
    else:
        print(f"Request failed: {result.get('error')}")


def cmd_send(args):
    if not ensure_daemon():
        return
    result = send_to_daemon({
        "action": "send",
        "path": args.path,
        "suggested_path": args.suggested_path or args.path,
    })
    if result.get("ok"):
        print("File sent successfully.")
    else:
        print(f"Send failed: {result.get('error')}")


def cmd_status(args):
    if daemon_is_running():
        result = send_to_daemon({"action": "status"})
        print(f"Status: {result.get('status')}")
    else:
        print("Daemon is not running.")


def cmd_dirs(args):
    if not ensure_daemon():
        return
    result = send_to_daemon({"action": "dirs"})
    directories = result.get("directories", [])
    if not directories:
        print("No shared directories configured.")
        return
    print("\nShared directories:")
    for d in directories:
        print(f"  {d}")
    print()


def cmd_add_dir(args):
    add_path()


def cmd_peers(args):
    peers = load_peers()
    if not peers:
        print("No saved peers.")
        return
    print("\nSaved peers:")
    for p in peers:
        print(f"  {p['name']}  {p['ip']}:{p['port']}  (last: {p['last_connected']})")
    print()


def cmd_forget(args):
    forget_peer(args.ip)
    print(f"Forgot peer {args.ip}")


def cmd_quit(args):
    if not daemon_is_running():
        print("Daemon is not running.")
        return
    result = send_to_daemon({"action": "quit"})
    if result and result.get("ok"):
        print("Session closed.")


def main():
    parser = argparse.ArgumentParser(prog="envshare", description="Secure .env file sharing tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_host = subparsers.add_parser("host", help="Start as host and wait for a connection")
    p_host.add_argument("--port", type=int, default=44444, help="Port to listen on")
    p_host.set_defaults(func=cmd_host)

    p_connect = subparsers.add_parser("connect", help="Connect to a host")
    p_connect.add_argument("address", help="IP address of the host")
    p_connect.add_argument("--port", type=int, default=44444, help="Port to connect to")
    p_connect.set_defaults(func=cmd_connect)

    p_list = subparsers.add_parser("list", help="List available .env files")
    p_list.add_argument("--local", action="store_true", help="List local files instead of remote")
    p_list.set_defaults(func=cmd_list)

    p_request = subparsers.add_parser("request", help="Request a file from the peer")
    p_request.add_argument("path", help="Path of the file to request")
    p_request.add_argument("--save-to", dest="save_to", help="Local path to save the file")
    p_request.set_defaults(func=cmd_request)

    p_send = subparsers.add_parser("send", help="Send a file to the peer")
    p_send.add_argument("path", help="Path of the file to send")
    p_send.add_argument("--as", dest="suggested_path", help="Suggested save path on the peer")
    p_send.set_defaults(func=cmd_send)

    p_status = subparsers.add_parser("status", help="Show connection status")
    p_status.set_defaults(func=cmd_status)

    p_dirs = subparsers.add_parser("dirs", help="Show shared directories")
    p_dirs.set_defaults(func=cmd_dirs)

    p_add = subparsers.add_parser("add-dir", help="Add a shared directory")
    p_add.set_defaults(func=cmd_add_dir)

    p_peers = subparsers.add_parser("peers", help="List saved peers")
    p_peers.set_defaults(func=cmd_peers)

    p_forget = subparsers.add_parser("forget", help="Forget a saved peer")
    p_forget.add_argument("ip", help="IP address of the peer to forget")
    p_forget.set_defaults(func=cmd_forget)

    p_quit = subparsers.add_parser("quit", help="Close the session")
    p_quit.set_defaults(func=cmd_quit)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
