import subprocess
import sys
import os


def run_command(command, error_message):
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Error: {error_message}")
        return False
    except FileNotFoundError:
        print(
            f"Error: Required command not found. Make sure all dependencies are installed."
        )
        return False


def main():
    # Check if we're in the correct directory (where pyproject.toml exists)
    if not os.path.exists("pyproject.toml"):
        print(
            "Error: pyproject.toml not found. Please run this script from the project root directory."
        )
        sys.exit(1)

    print("Setting up development environment...")

    # Install package in development mode
    print("\n1. Installing package...")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."], "Failed to install package"
    ):
        sys.exit(1)

    # Clean pre-commit environment
    print("\n2. Cleaning pre-commit environment...")
    if not run_command(
        ["pre-commit", "clean"],
        "Failed to clean pre-commit environment. Make sure pre-commit is installed: pip install pre-commit",
    ):
        sys.exit(1)

    # Install pre-commit hooks
    print("\n3. Installing pre-commit hooks...")
    if not run_command(
        ["pre-commit", "install"],
        "Failed to install pre-commit hooks. Make sure pre-commit is installed: pip install pre-commit",
    ):
        sys.exit(1)

    print("\nSetup complete! Your development environment is ready.")
    print("Black formatting will run automatically on commits and GitHub actions.")


if __name__ == "__main__":
    main()
