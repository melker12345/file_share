import json
import os
from datetime import datetime

from config import PEERS_FILE


def load_peers():
    if not os.path.exists(PEERS_FILE):
        return []
    with open(PEERS_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("peers", [])
        except json.JSONDecodeError:
            return []


def _save_peers(peers):
    with open(PEERS_FILE, "w") as f:
        json.dump({"peers": peers}, f, indent=2)


def save_peer(ip, port, shared_secret, name=None):
    peers = load_peers()

    # Update existing peer or add new one
    for peer in peers:
        if peer["ip"] == ip and peer["port"] == port:
            peer["shared_secret_hex"] = shared_secret.hex()
            peer["last_connected"] = datetime.now().isoformat()
            if name:
                peer["name"] = name
            _save_peers(peers)
            return

    peers.append({
        "ip": ip,
        "port": port,
        "name": name or ip,
        "shared_secret_hex": shared_secret.hex(),
        "last_connected": datetime.now().isoformat(),
    })
    _save_peers(peers)


def find_peer(ip, port=44444):
    peers = load_peers()
    for peer in peers:
        if peer["ip"] == ip and peer["port"] == port:
            return peer
    return None


def get_shared_secret(peer):
    return bytes.fromhex(peer["shared_secret_hex"])


def forget_peer(ip):
    peers = load_peers()
    peers = [p for p in peers if p["ip"] != ip]
    _save_peers(peers)
