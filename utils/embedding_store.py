import pickle
import os

FILE_PATH = "dataset/embeddings.pkl"

def load_embeddings():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "rb") as f:
            return pickle.load(f)
    return {}

def save_embeddings(data):
    with open(FILE_PATH, "wb") as f:
        pickle.dump(data, f)