import os

# Here the ~ will not be expanded 
# so we need to find a way to do it manually.
PATH = os.path.expanduser("~/.config/envshare/")
SHARED_DIR = os.path.join(PATH, "shared_dir.txt")
CONFIG = os.path.join(PATH, "config.conf")
PEERS_FILE = os.path.join(PATH, "peers.json")
PID_FILE = os.path.join(PATH, "daemon.pid")
RECEIVED_DIR = os.path.join(PATH, "received")
os.makedirs(PATH, exist_ok=True)
os.makedirs(RECEIVED_DIR, exist_ok=True)

# INIT the conf files and shared_dirs
# This makes the path and files
def create_config_files():
    if not os.path.exists(SHARED_DIR):
        with open(SHARED_DIR, "x") as f:
            f.write("")
        
    if not os.path.exists(CONFIG):
        with open(CONFIG, "x") as f:
            f.write("")
    
create_config_files()

def check_path(shared_dir):
    if os.path.exists(shared_dir):
        return True
    else:
        print("Not a valid directory buddy :/")
        return False

def add_path():
    shared_dir = input("Enter directory to append new shared dir: \n")
    if check_path(shared_dir):
        if shared_dir in read_list():
            print("already added")
        else:
            with open(SHARED_DIR, "a") as f:
                f.write(shared_dir + "\n")
                print(shared_dir)

# reads the paths added to PATH + SHARED_DIR.
def read_list():
    x = []
    with open(SHARED_DIR, "r") as f:
        for i in f:
            x.append(str.strip(i))
    return x
