import subprocess
from typing import Set, Dict
import tomli
from pathlib import Path

def load_pyproject_dependencies() -> Set[str]:
    """Load dependencies from pyproject.toml."""
    try:
        with open("pyproject.toml", "rb") as f:
            pyproject = tomli.load(f)
            return set(pyproject["project"]["dependencies"])
    except FileNotFoundError:
        print("Error: pyproject.toml not found")
        return set()
    except KeyError:
        print("Error: Could not find dependencies in pyproject.toml")
        return set()

def get_pipdeptree_deps() -> Dict[str, Set[str]]:
    """Get both direct and indirect dependencies from pipdeptree."""
    try:
        result = subprocess.run(
            ['pipdeptree', '-p', 'academic_metrics', '--json'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("Error running pipdeptree:", result.stderr)
            return {}, {}
            
        import json
        tree = json.loads(result.stdout)
        
        direct_deps = set()
        indirect_deps = set()
        
        # Process the dependency tree
        for package in tree:
            if package['package']['key'] == 'academic_metrics':
                for dep in package['dependencies']:
                    direct_deps.add(dep['package']['key'])
                    # Get indirect dependencies
                    for indirect in dep['dependencies']:
                        indirect_deps.add(indirect['package']['key'])
        
        return {
            'direct': direct_deps,
            'indirect': indirect_deps
        }
    except subprocess.CalledProcessError:
        print("Error: Failed to run pipdeptree. Make sure it's installed.")
        return {}, {}
    except json.JSONDecodeError:
        print("Error: Failed to parse pipdeptree JSON output")
        return {}, {}

def scan_imports(directory: str = "src") -> Set[str]:
    """Scan Python files for import statements."""
    import ast
    import glob
    
    imports = set()
    
    def extract_imports(node):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    
    for py_file in glob.glob(f"{directory}/**/*.py", recursive=True):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    extract_imports(node)
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")
    
    return imports

def main():
    # Get all dependencies
    pyproject_deps = load_pyproject_dependencies()
    dep_tree = get_pipdeptree_deps()
    actual_imports = scan_imports()
    
    # Analysis
    unused_in_code = pyproject_deps - actual_imports
    not_in_tree = pyproject_deps - dep_tree['direct'] - dep_tree['indirect']
    
    # Output results
    print("=== Dependency Analysis ===\n")
    
    print("Dependencies in pyproject.toml:", len(pyproject_deps))
    print("Direct dependencies (pipdeptree):", len(dep_tree['direct']))
    print("Indirect dependencies (pipdeptree):", len(dep_tree['indirect']))
    print("Actually imported packages:", len(actual_imports))
    
    print("\n=== Potential Issues ===")
    
    print("\nDependencies listed in pyproject.toml but not imported in code:")
    for dep in sorted(unused_in_code):
        print(f"- {dep}")
    
    print("\nDependencies in pyproject.toml but not found in dependency tree:")
    for dep in sorted(not_in_tree):
        print(f"- {dep}")
    
    print("\nNote:")
    print("1. Some dependencies might be runtime-only")
    print("2. Some might be development dependencies that should be in [tool.poetry.dev-dependencies]")
    print("3. Some might use different import names than their package names")
    print("4. Some might be transitive dependencies that could be removed")

if __name__ == "__main__":
    main()