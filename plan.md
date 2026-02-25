# envshare — Secure .env File Sharing Tool

## Problem

Syncing `.env` files across machines is tedious and insecure. Copy-pasting through chat, email, or cloud storage risks leaking secrets. This tool solves that by enabling direct, encrypted, peer-to-peer `.env` sharing over the network.

---

## Learning Mode

This project is a learning exercise. The AI assistant acts as a **teacher, not a coder**:

- **Never** give me ready-made code. Guide me to the answer instead.
- Point me to the relevant **Python docs**, **`cryptography` library docs**, or **man pages** where I can find what I need.
- When I'm stuck, give **hints** — explain the concept, name the function/module I should look at, or describe the approach in pseudocode. Let me write the actual code.
- Ask me **questions** to help me think through the problem ("What happens if the socket closes mid-transfer? How would you handle that?").
- If I've made a mistake, explain **why** it's wrong and point me toward the fix — don't just fix it for me.
- It's fine to show **small snippets** (1-3 lines) to illustrate a syntax point or API usage, but never write whole functions or modules for me.

The goal is for me to understand every line I write, not just have a working project.

---

## How It Works (User Flow)

### 1. First Run — Pairing

Both machines run the same script. One acts as **host**, the other as **client**.

```
PC-A $ envshare host
  Listening on 192.168.1.164:44445 ...
  Connected to PC-B
  Verification code: 7291
  Does this match the other machine? [y/n]: y
  Paired! Session active. Running in background.

PC-B $ envshare connect 192.168.1.164
  Connected to PC-A
  Verification code: 7291
  Does this match the other machine? [y/n]: y
  Paired! Session active. Running in background.
```

- X25519 key exchange happens automatically on connect.
- Both sides see a short numeric verification code (derived from the shared secret).
- User confirms the codes match — this prevents MITM attacks.
- After confirmation, a background daemon keeps the session alive.

### 2. Background Daemon

After pairing, the process daemonizes (or stays as a background process). It:

- Listens for incoming commands from the peer.
- Listens for local CLI commands via a Unix domain socket (or localhost TCP).
- Keeps the connection alive with periodic heartbeats.
- Session lasts **all day** (or until `envshare quit` is run on either side).

### 3. CLI Commands (after pairing)

All commands talk to the local background daemon, which relays to/from the peer.

| Command | Description |
|---|---|
| `envshare list` | List all `.env` files the **remote** peer has available (path + project name) |
| `envshare list --local` | List all `.env` files in your own shared directories |
| `envshare request <path>` | Request a specific `.env` file from the peer |
| `envshare send <path>` | Push a specific `.env` file to the peer |
| `envshare add-dir <directory>` | Add a directory to scan for `.env` files |
| `envshare dirs` | Show currently shared directories |
| `envshare status` | Show connection status (peer IP, uptime, etc.) |
| `envshare quit` | Gracefully close the session on both sides |

### 4. Listing Files

When you run `envshare list`, the tool asks the peer for its available `.env` files. The peer recursively scans its shared directories and returns results like:

```
Remote .env files (PC-A):
  1. /home/user/projects/webapp/.env          (webapp)
  2. /home/user/projects/webapp/.env.local    (webapp)
  3. /home/user/projects/api/.env             (api)
  4. /home/user/projects/api/.env.production  (api)
```

The project name is inferred from the parent directory name.

### 5. Requesting / Sending Files

```
PC-B $ envshare request /home/user/projects/api/.env
  Requesting .env from PC-A...
  Received! Saved to: /home/me/projects/api/.env
  (File was encrypted in transit with ChaCha20-Poly1305)
```

The user is prompted to confirm the save location (defaults to matching relative path under their shared dir, or a specified path).

---

## Architecture

```
┌─────────────────────────────────────────┐
│                 CLI                      │
│  (envshare host | connect | list | ...) │
└──────────────┬──────────────────────────┘
               │ IPC (unix socket / localhost)
┌──────────────▼──────────────────────────┐
│          Background Daemon               │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ IPC Server │  │  Peer Connection  │  │
│  │ (local CLI)│  │  (TCP + TLS-like) │  │
│  └────────────┘  └───────────────────┘  │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ File       │  │  Crypto Layer     │  │
│  │ Scanner    │  │  (X25519 +        │  │
│  │ (.env)     │  │   ChaCha20Poly)   │  │
│  └────────────┘  └───────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Module Breakdown

### Existing (to keep / extend)

| File | Status | Purpose |
|---|---|---|
| `crypto.py` | Partially done | Key exchange, encrypt/decrypt. **Need:** finish `decrypt()`. |
| `config.py` | Partially done | Shared directory management. **Need:** refactor to use XDG paths or a config file in `~/.config/envshare/`. |

### To Implement

| File | Purpose |
|---|---|
| `main.py` | CLI entry point. Parses args (`host`, `connect`, `list`, `request`, `send`, `quit`, etc.). Dispatches to daemon or sends IPC commands. |
| `daemon.py` | Background process. Manages the TCP connection to peer, IPC socket for local CLI, heartbeats, and session lifecycle. |
| `connection.py` | TCP connection handling. Establishes connection (host binds + listens, client connects). Wraps send/recv with the crypto layer. |
| `protocol.py` | Message protocol. Defines message types (HANDSHAKE, LIST_REQUEST, LIST_RESPONSE, FILE_REQUEST, FILE_RESPONSE, QUIT, HEARTBEAT) and serialization (JSON envelope + binary payload). |
| `pairing.py` | Pairing flow. Orchestrates key exchange over TCP, displays verification code, waits for user confirmation, returns shared secret. |
| `discover.py` | (Future / optional) mDNS or UDP broadcast for LAN auto-discovery. For now, manual IP entry is fine. |
| `file_service.py` | Scans shared directories for `.env` files (recursive glob). Reads/writes `.env` files. Infers project names from paths. |
| `utils.py` | Helpers — logging, path normalization, display formatting. |

---

## Protocol Design

All messages are encrypted with ChaCha20-Poly1305 using the shared secret after pairing.

### Message Format

```
[4 bytes: message length (big-endian)] [encrypted payload]
```

Decrypted payload is JSON:

```json
{
  "type": "LIST_REQUEST | LIST_RESPONSE | FILE_REQUEST | FILE_RESPONSE | QUIT | HEARTBEAT",
  "data": { ... }
}
```

### Message Types

| Type | Direction | Data |
|---|---|---|
| `LIST_REQUEST` | requester → peer | `{}` |
| `LIST_RESPONSE` | peer → requester | `{"files": [{"path": "...", "project": "...", "size": 123}, ...]}` |
| `FILE_REQUEST` | requester → peer | `{"path": "/home/user/project/.env"}` |
| `FILE_RESPONSE` | peer → requester | `{"path": "...", "content": "base64-encoded-content", "ok": true}` or `{"ok": false, "error": "..."}` |
| `SEND` | sender → peer | `{"path": "...", "content": "base64-encoded", "suggested_path": "..."}` |
| `QUIT` | either → peer | `{}` |
| `HEARTBEAT` | either → peer | `{}` (sent every 60s, timeout at 180s) |

---

## Security Model

1. **X25519 Diffie-Hellman** key exchange — ephemeral keys per session.
2. **Verification code** — short numeric code derived from `SHA-256(shared_secret)`. Both users confirm it matches out-of-band (visual comparison) to prevent MITM.
3. **ChaCha20-Poly1305** authenticated encryption — all messages after pairing are encrypted + integrity-checked.
4. **No persistent keys** — each session generates fresh keys. No certificates, no PKI. Simple and secure.
5. **File content never touches disk unencrypted in transit** — decrypted only at the destination.

---

## Implementation Order

### Phase 1 — Core (MVP)
1. Finish `crypto.py` — implement `decrypt()`, add message framing helpers.
2. Build `protocol.py` — message types, serialization, length-prefixed framing.
3. Build `connection.py` — TCP connection with crypto layer baked in.
4. Build `pairing.py` — key exchange + verification code flow.
5. Build `file_service.py` — recursive `.env` scanner, read/write helpers.
6. Build `daemon.py` — background process with peer connection + local IPC socket.
7. Build `main.py` — CLI with argparse (`host`, `connect`, `list`, `request`, `send`, `quit`).

### Phase 2 — Polish
8. Add `--save-to <path>` option for `request` command.
9. Heartbeat + reconnect logic.
10. Colored terminal output + progress indicators.
11. `requirements.txt` and `README.md`.
12. `.gitignore` (venv, __pycache__, shared_dir.txt).

### Phase 3 — Nice to Have
13. LAN auto-discovery via UDP broadcast (`discover.py`).
14. Multiple simultaneous peers.
15. File change watching + auto-sync mode.
16. Transfer history / audit log.

---

## Tech Stack

- **Python 3.10+** (standard library + `cryptography`)
- **TCP sockets** for peer communication
- **Unix domain socket** (Linux/Mac) for CLI ↔ daemon IPC
- **`cryptography`** library for X25519 + ChaCha20-Poly1305
- **argparse** for CLI
- **`os.walk`** or **`pathlib.glob`** for `.env` file discovery

---

## Open Questions

1. [ ] Should the daemon auto-accept incoming file sends, or always prompt the user?
2. [ ] Should we support `.env.*` variants (`.env.local`, `.env.production`) or only exact `.env`?
3. [ ] Config file location — `~/.config/envshare/config.json` vs local `shared_dir.txt`?
4. [ ] Port selection — fixed (44445) or configurable?

1. If PC A is requesting a file from PC B. we can have a confirmation on pc A but PC B should just send the file. This allows me to interact less with both PCs for better UX

2. Yes i want this to be configurable, the user should be able to send different files also but main focus is env and all variants.

3. Sure we can put it in the .config.

4. Port should also be configurable but as default we can have something like 44445