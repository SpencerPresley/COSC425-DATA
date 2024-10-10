import os
import ast


def find_imports(file_path):
    with open(file_path, "r") as file:
        tree = ast.parse(file.read())

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:  # Exclude relative imports
                imports.add(node.module.split(".")[0])
    return imports


def is_standard_library(module):
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def is_local_module(module, local_modules, custom_modules):
    return module in local_modules or module in custom_modules


def main():
    codebase_dir = "."  # Current directory
    all_imports = set()
    local_modules = set()
    custom_modules = {"Utilities", "DeducedData"}  # Add any other custom modules here

    # First pass: collect all local module names
    for root, dirs, files in os.walk(codebase_dir):
        for file in files:
            if file.endswith(".py"):
                local_modules.add(os.path.splitext(file)[0])

    # Second pass: collect all imports
    for root, dirs, files in os.walk(codebase_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(f"Processing: {file_path}")  # Add this line
                all_imports.update(find_imports(file_path))

    # Filter out standard library, local modules, and custom modules
    third_party_imports = {
        module
        for module in all_imports
        if not is_standard_library(module)
        and not is_local_module(module, local_modules, custom_modules)
    }

    for module in third_party_imports:
        print(module)

    # Write requirements.txt
    with open("requirements.txt", "w") as req_file:
        for module in sorted(third_party_imports):
            req_file.write(f"{module}\n")

    print("requirements.txt file has been generated.")


if __name__ == "__main__":
    main()
