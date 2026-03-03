from pathlib import Path
from config import read_list


def scan_env_files(directories, pattern=".env*"):
    found_files = []

    for directory in directories:
        p = Path(directory)
        for file_path in p.rglob(pattern):
            if file_path.is_file():
                found_files.append({
                    "path": str(file_path),
                    "project": file_path.parent.name,
                    "size": file_path.stat().st_size,
                })

    return found_files


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


def write_file(path, content):
    with open(path, "wb") as f:
        f.write(content)
