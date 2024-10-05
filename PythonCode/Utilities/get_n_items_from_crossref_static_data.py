import ijson
import json


def save_items_to_file(*, path: str, items: list[dict]) -> None:
    with open(path, "w") as f:
        json.dump(items, f, indent=4)
    print("Saved Successfully")


def get_n_items(*, n, path):
    with open(path, "r") as f:
        data = json.load(f)
    save_items_to_file(path="n-paper-doi-list", items=data[:n])


if __name__ == "__main__":
    n = 10
    path = "./paper-doi-list.json"
    get_n_items(n=n, path=path)
