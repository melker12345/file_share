import argparse
import json
import socket
import sys

from connection import host, connect
from pairing import pairing_host, pairing_client
from daemon import run_daemon, SOCK_PATH
from config import add_path


def send_to_daemon(command):
    """Connect to the running daemon via IPC socket, send a command, return the response."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCK_PATH)
        sock.send(json.dumps(command).encode())
        response = sock.recv(65536)
        sock.close()
        return json.loads(response.decode())
    except ConnectionRefusedError:
        print("Daemon is not running. Start with 'envshare host' or 'envshare connect <ip>' first.")
        sys.exit(1)
    except FileNotFoundError:
        print("Daemon is not running. Start with 'envshare host' or 'envshare connect <ip>' first.")
        sys.exit(1)


def cmd_host(args):
    print(f"Listening on port {args.port}...")
    con, addr = host(port=args.port)
    print(f"Connected to {addr[0]}")

    shared_secret = pairing_host(con)
    if shared_secret is None:
        print("Pairing rejected. Closing connection.")
        con.close()
        return

    run_daemon(con, shared_secret)


def cmd_connect(args):
    print(f"Connecting to {args.address}:{args.port}...")
    sock = connect(args.address, port=args.port)
    print("Connected!")

    shared_secret = pairing_client(sock)
    if shared_secret is None:
        print("Pairing rejected. Closing connection.")
        sock.close()
        return

    run_daemon(sock, shared_secret)


def cmd_list(args):
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
    command = {"action": "request", "path": args.path}
    if args.save_to:
        command["save_to"] = args.save_to

    result = send_to_daemon(command)
    if result.get("ok"):
        print(f"File received and saved to: {result['saved_to']}")
    else:
        print(f"Request failed: {result.get('error')}")


def cmd_send(args):
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
    result = send_to_daemon({"action": "status"})
    print(f"Status: {result.get('status')}")


def cmd_dirs(args):
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


def cmd_quit(args):
    result = send_to_daemon({"action": "quit"})
    if result.get("ok"):
        print("Session closed.")


def main():
    parser = argparse.ArgumentParser(prog="envshare", description="Secure .env file sharing tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # host
    p_host = subparsers.add_parser("host", help="Start as host and wait for a connection")
    p_host.add_argument("--port", type=int, default=44444, help="Port to listen on")
    p_host.set_defaults(func=cmd_host)

    # connect
    p_connect = subparsers.add_parser("connect", help="Connect to a host")
    p_connect.add_argument("address", help="IP address of the host")
    p_connect.add_argument("--port", type=int, default=44444, help="Port to connect to")
    p_connect.set_defaults(func=cmd_connect)

    # list
    p_list = subparsers.add_parser("list", help="List available .env files")
    p_list.add_argument("--local", action="store_true", help="List local files instead of remote")
    p_list.set_defaults(func=cmd_list)

    # request
    p_request = subparsers.add_parser("request", help="Request a file from the peer")
    p_request.add_argument("path", help="Path of the file to request")
    p_request.add_argument("--save-to", dest="save_to", help="Local path to save the file")
    p_request.set_defaults(func=cmd_request)

    # send
    p_send = subparsers.add_parser("send", help="Send a file to the peer")
    p_send.add_argument("path", help="Path of the file to send")
    p_send.add_argument("--as", dest="suggested_path", help="Suggested save path on the peer")
    p_send.set_defaults(func=cmd_send)

    # status
    p_status = subparsers.add_parser("status", help="Show connection status")
    p_status.set_defaults(func=cmd_status)

    # dirs
    p_dirs = subparsers.add_parser("dirs", help="Show shared directories")
    p_dirs.set_defaults(func=cmd_dirs)

    # add-dir
    p_add = subparsers.add_parser("add-dir", help="Add a shared directory")
    p_add.set_defaults(func=cmd_add_dir)

    # quit
    p_quit = subparsers.add_parser("quit", help="Close the session")
    p_quit.set_defaults(func=cmd_quit)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
