import numpy as np
import json


def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


def count_entries_in_json(json_file):
    # Load and parse the JSON file
    with open(json_file, "r") as file:
        data = json.load(file)

    # Check if data is a list of entries
    if isinstance(data, list):
        return len(data)
    else:
        # Raise an error if the structure is not a list
        raise ValueError("JSON structure is not as expected. Expected a list of objects.")


def json_to_numpy_matrix(json_file):
    with open(json_file, "r") as file:
        data = json.load(file)

    # Since all values are numerical, extract them directly
    numeric_data = [list(entry.values()) for entry in data]

    # Convert the list of lists into a NumPy matrix
    matrix = np.array(numeric_data)

    return matrix


def get_json_column_labels(json_file):
    with open(json_file, "r") as file:
        data = json.load(file)

    # Assuming all objects have the same keys,
    # extract the keys from the first object
    if len(data) > 0 and isinstance(data, list) and isinstance(data[0], dict):
        column_labels = list(data[0].keys())
        return column_labels
    else:
        raise ValueError("JSON structure is not as expected or is empty.")
