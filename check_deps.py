import os
import ast
from collections import defaultdict
from pathlib import Path


def is_external_import(module_name):
    """Check if an import is from an external library."""
    # List of Python standard library modules
    stdlib_modules = set(sys.stdlib_module_names)
    base_module = module_name.split(".")[0]
    return base_module not in stdlib_modules and not module_name.startswith(
        "academic_metrics"
    )


def analyze_imports(file_path):
    """Analyze imports in a Python file."""
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            tree = ast.parse(file.read())
        except:
            return []

    external_imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                if is_external_import(name.name):
                    external_imports.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and is_external_import(node.module):
                external_imports.add(node.module)

    return external_imports


def find_all_external_imports(directory):
    """Find all external imports in Python files within a directory."""
    imports_by_file = defaultdict(set)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                external_imports = analyze_imports(file_path)
                if external_imports:
                    imports_by_file[file_path] = external_imports

    return imports_by_file


if __name__ == "__main__":
    import sys

    # Use the directory path from the code blocks
    directory = "src/academic_metrics"

    # Get all external imports
    all_imports = find_all_external_imports(directory)

    # Print results
    print("\nExternal Libraries Used by File:\n")
    for file_path, imports in all_imports.items():
        print(f"\n{file_path}:")
        for imp in sorted(imports):
            print(f"  - {imp}")

    # Print summary of all unique external libraries
    all_unique_imports = sorted(set().union(*all_imports.values()))
    print("\nAll Unique External Libraries:\n")
    for imp in all_unique_imports:
        print(f"- {imp}")
