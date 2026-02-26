from config import read_list
import glob

def scan_env_files():
    x = read_list()
    allowed_files = []
    for i in range(len(x)):
        allowed_files.append(glob.glob(f"{x[i]}/*.env*"))
    print(allowed_files)

scan_env_files()