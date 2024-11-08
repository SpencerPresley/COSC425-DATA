import ijson
import json


def save_items_to_file(*, path: str, items: list[dict]) -> None:
    with open(path, "w") as f:
        json.dump(items, f, indent=4)
    print("Saved Successfully")


def get_n_items(*, path):
    n = 0
    with open(path, "r") as f:
        data = json.load(f)
    n = len(data)
    save_items_to_file(path=f"input_files/{n}-paper-doi-list.json", items=data)


if __name__ == "__main__":
    path = "./test.json"
    get_n_items(path=path)
