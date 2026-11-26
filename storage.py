import json
import os

#contains read/write function
def read_data(filename):
    if not os.path.exists(filename):
        return []

    with open(filename, "r") as file:
        return json.load(file)

def write_data(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
