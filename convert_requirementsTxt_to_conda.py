import subprocess
import os


def get_conda_package(pip_package):
    # Remove version specifiers
    package_name = pip_package.split("==")[0].split(">=")[0].split("<=")[0]

    # Check if the package exists in conda
    result = subprocess.run(
        ["conda", "search", package_name, "--json"], capture_output=True, text=True
    )

    if "error" not in result.stdout.lower():
        return package_name
    else:
        # If not found in conda, suggest using pip within conda
        return f"pip install {pip_package}"


def main():
    with open("requirements.txt", "r") as f:
        requirements = f.read().splitlines()

    conda_commands = []
    pip_commands = []

    for req in requirements:
        if req.strip() and not req.startswith("#"):
            package = get_conda_package(req)
            if package.startswith("pip install"):
                pip_commands.append(package)
            else:
                conda_commands.append(f"conda install -y {package}")

    # Write commands to a shell script
    with open("install_packages.sh", "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write(
            "# Activate conda environment (uncomment and replace with your environment name)\n"
        )
        f.write("# conda activate your_environment_name\n\n")
        f.write("# Conda install commands\n")
        f.write(" && ".join(conda_commands))
        f.write("\n\n")
        if pip_commands:
            f.write("# Packages not found in conda (install with pip)\n")
            f.write(" && ".join(pip_commands))
            f.write("\n")

    # Make the script executable
    os.chmod("install_packages.sh", 0o755)

    print("Shell script 'install_packages.sh' has been created.")
    print("You can run it with: ./install_packages.sh")


if __name__ == "__main__":
    main()
