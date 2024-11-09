import subprocess
import sys
import os


def run_command(command, error_message, cwd=None):
    try:
        subprocess.run(command, check=True, cwd=cwd)
        return True
    except subprocess.CalledProcessError:
        print(f"Error: {error_message}")
        return False
    except FileNotFoundError:
        print(
            f"Error: Required command not found. Make sure all dependencies are installed."
        )
        return False


def setup_git_hooks():
    """Set up git hooks by appending black formatting to the pre-commit hook"""
    # Get the project root directory (where pyproject.toml is)
    project_root = os.path.dirname(os.path.abspath(__file__))
    git_hooks_dir = os.path.join(project_root, ".git", "hooks")
    pre_commit_path = os.path.join(git_hooks_dir, "pre-commit")
    
    # Ensure the hooks directory exists
    os.makedirs(git_hooks_dir, exist_ok=True)
    
    # If the file doesn't exist, create it with a shebang
    if not os.path.exists(pre_commit_path):
        with open(pre_commit_path, 'w') as f:
            f.write("#!/bin/bash\n\n")
    
    # Append our black formatting commands
    with open(pre_commit_path, 'a') as f:
        f.write("\n# Added by setup_environment.py - Black formatting\n")
        f.write("PROJECT_ROOT=$(git rev-parse --show-toplevel)\n")
        f.write("cd \"$PROJECT_ROOT\"\n")
        f.write("black .\n")
        f.write("# Stage only Python files that were modified by black\n")
        f.write("git diff --name-only | grep '.py$' | xargs -I {} git add {}\n")
    
    # Make the script executable
    os.chmod(pre_commit_path, 0o755)
    
    return True


def main():
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we're in the correct directory (where pyproject.toml exists)
    if not os.path.exists(os.path.join(project_root, "pyproject.toml")):
        print(
            "Error: pyproject.toml not found. Please run this script from the project root directory."
        )
        sys.exit(1)

    print("Setting up development environment...")

    # Install package in development mode
    print("\n1. Installing package...")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        "Failed to install package",
        cwd=project_root
    ):
        sys.exit(1)

    # Install git hooks
    print("\n2. Setting up git hooks...")
    if not setup_git_hooks():
        print("Failed to set up git hooks")
        sys.exit(1)

    print("\nSetup complete! Your development environment is ready.")
    print("Black formatting will run automatically on commits.")


if __name__ == "__main__":
    main()