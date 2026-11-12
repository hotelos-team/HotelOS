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

# jsonl

def read_records(filename):
    records = []
    with open(filename, "r") as file:
        for line in file:
            records.append(json.loads(line))
        
    return records

def load_records(filename, id_field):
    records = {}
    with open(filename, "r") as file:
        for line in file:
            record = json.loads(line)
            records[record[id_field]] = record

    return records

def append_change(filename, data):
    with open(filename, "a") as file:
        file.write(json.dumps(data) + "\n")