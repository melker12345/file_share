import os

# Here the ~ will not be expanded 
# so we need to find a way to do it manually.
PATH = os.path.expanduser("~/.config/envshare/")
SHARED_DIR = PATH + "shared_dir.txt"
CONFIG = PATH + "config.conf"
os.makedirs(PATH, exist_ok=True)

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
    shared_dir = input("Enter directory to append new shared dir")
    if check_path(shared_dir):
        if shared_dir in read_list():
            print("already added")
        else:
            with open(SHARED_DIR, "a") as f:
                f.write(shared_dir + "\n")
                print(shared_dir)        

    else:
        print("Not a valid directory")

# reads the paths added to PATH + SHARED_DIR.
def read_list():
    x = []
    with open(SHARED_DIR, "r") as f:
        for i in f:
            x.append(str.strip(i))
    print(x)
    return x

add_path()