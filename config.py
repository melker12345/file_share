import os

def check_path(shared_dir):
    if os.path.exists(shared_dir):
        return True
    else:
        print("Not a valid directory buddy :/")
        return False

def add_path():
    shared_dir = input("Enter directory to append new shared dir")

    if check_path(shared_dir):
        if os.path.getsize("shared_dir.txt") == 0:
            with open("shared_dir.txt", "w") as f:
                f.write(shared_dir + "\n")
                print(shared_dir)
        else:
            with open("shared_dir.txt", "a") as f:
                f.write(shared_dir + "\n")
                print(shared_dir)

    else:
        print("Not a valid directory")

def read_list():
    list = []
    with open("shared_dir.txt", "r") as f:
        for i in f:
            list.append(i)
    return list
