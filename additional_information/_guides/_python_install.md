# Python Installation Guide

## Introduction

This guide covers the installation of Python 3.12, a powerful and widely-used programming language. Python is known for its:

- Clear, readable syntax
- Large ecosystem of packages and libraries
- Strong community support
- Cross-platform compatibility

We'll walk through:

1. Installing Python on your operating system
2. Verifying the installation
3. Setting up your development environment
4. Managing packages and dependencies

## Table of Contents

- [Python Installation Guide](#python-installation-guide)
  - [Introduction](#introduction)
  - [Table of Contents](#table-of-contents)
  - [Installation by Operating System](#installation-by-operating-system)
    - [Windows Installation](#windows-installation)
      - [Method 1: Microsoft Store (Simplest)](#method-1-microsoft-store-simplest)
      - [Method 2: Python.org Installer (Recommended)](#method-2-pythonorg-installer-recommended)
      - [Post-Installation (Windows)](#post-installation-windows)
    - [macOS Installation](#macos-installation)
      - [Method 1: Homebrew (Recommended)](#method-1-homebrew-recommended)
      - [Method 2: Python.org Installer](#method-2-pythonorg-installer)
      - [Post-Installation (macOS)](#post-installation-macos)
    - [Linux Installation](#linux-installation)
      - [Ubuntu/Debian](#ubuntudebian)
      - [Fedora](#fedora)
      - [Post-Installation (Linux)](#post-installation-linux)
  - [Understanding Virtual Environments](#understanding-virtual-environments)
  - [Setting Up Virtual Environments](#setting-up-virtual-environments)
    - [Using venv (Built-in)](#using-venv-built-in)
      - [1. Create a new virtual environment](#1-create-a-new-virtual-environment)
      - [2. Activate the environment](#2-activate-the-environment)
    - [Using Conda (Recommended)](#using-conda-recommended)
      - [1. Install Miniconda](#1-install-miniconda)
      - [2. Create a new environment](#2-create-a-new-environment)
      - [3. Activate the environment](#3-activate-the-environment)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
      - [1. Python not found in PATH](#1-python-not-found-in-path)
      - [2. Permission Issues](#2-permission-issues)
      - [3. Multiple Python Versions](#3-multiple-python-versions)
  - [Package Management](#package-management)
    - [Using pip (Python Package Installer)](#using-pip-python-package-installer)
  - [Additional Resources](#additional-resources)
  - [Getting Help](#getting-help)

</br>

## Installation by Operating System

### Windows Installation

#### Method 1: Microsoft Store (Simplest)

1. Open the Microsoft Store
2. Search for "Python 3.12"
3. Click "Get" or "Install"
4. Open Command Prompt and verify with `python --version`

#### Method 2: Python.org Installer (Recommended)

1. Visit [Python Downloads](https://www.python.org/downloads/)
2. Download Python 3.12 installer
3. Run the installer with these important settings:
   - ✅ Add python.exe to PATH (Required)
   - ✅ Install pip (Should be selected by default)
   - ✅ Install for all users (Recommended)
4. Click "Install Now" for standard installation or "Customize installation" for advanced options

#### Post-Installation (Windows)

1. Open Command Prompt (cmd) or PowerShell
2. Verify installation:

   ```bash
   python --version    # Should show: Python 3.12.x
   pip --version      # Should show: pip X.Y.Z
   ```

</br>

### macOS Installation

#### Method 1: Homebrew (Recommended)

1. Install Homebrew if not present (you can check if it's installed by running `brew --version`):

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install Python:

   ```bash
   brew install python@3.12
   ```

3. Add to PATH (if not automatically added):

   ```bash
   echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

#### Method 2: Python.org Installer

1. Visit [Python Downloads](https://www.python.org/downloads/)
2. Download macOS installer
3. Run the package installer
4. Follow the installation wizard

#### Post-Installation (macOS)

1. Open Terminal
2. Verify installation:

   ```bash
   python3 --version   # Should show: Python 3.12.x
   pip3 --version     # Should show: pip X.Y.Z
   ```

### Linux Installation

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3-pip
```

#### Fedora

```bash
sudo dnf install python3.12 python3.12-pip python3.12-devel
```

#### Post-Installation (Linux)

```bash
python3.12 --version  # Should show: Python 3.12.x
pip3 --version       # Should show: pip X.Y.Z
```

</br>

## Understanding Virtual Environments

> [!IMPORTANT]  
> Now that you have Python installed, it's important to understand virtual environments. They are a crucial tool for Python development that:
>
> - Isolate project dependencies to avoid conflicts
> - Make projects reproducible across different machines
> - Allow you to work on multiple projects with different Python versions
> - Prevent system-wide Python installation issues
>
> Using a virtual environment is optional, but is highly recommended, if you'd like to use a virtual environment, the below section will guide you step by step through the process of setting one up. It is quite simple and easy to do, and can be completed in only a couple of minutes.

</br>

## Setting Up Virtual Environments

> [!NOTE]  
> This section of the guide should be followed only after you have created a directory and entered it.
>
> The section that covers that can be found in the [README.md](../../README.md) file's [2. Creating the directory and necessary files](../../README.md#2-creating-the-directory-and-necessary-files) section.
>
> You'll find the link back to this section in the [README.md](../../README.md) file's [3. Setting up a Virtual Environment (Optional but Recommended)](../../README.md#3-setting-up-a-virtual-environment-optional-but-recommended) section.

</br>

### Using venv (Built-in)

> [!NOTE]  
> Though you will still be using pip to install the Academic Metrics package, I still recommend using Conda for your virtual environments.
>
> Conda in addition to being a more powerful package manager that helps alleviate some of the issues that can arise from using pip, it also provides a more user friendly interface for managing different virtual environments; including creation, activation, and deactivation.
>
> If you'd like to use Conda, skip to the [Using Conda Section](#using-conda-recommended)
>
> Otherwise, continue with the following steps to create a new virtual environment using the built-in venv module.

</br>

#### 1. Create a new virtual environment

**Windows**:

```bash
python -m venv <env_name>
```

**macOS/Linux**:

There's a useful tip outlined in [this](#3-multiple-python-versions) section which covers **aliasing** the `python` and `pip` commands to use the version you'd like to use, it will streamline the below process and only takes a couple of seconds to do.

If you'd like to take advantage of aliasing, follow the above link to that section, complete the steps outlined in the tip, then come back to this section.

Otherwise, continue forward with this section.

```bash
python -m venv <env_name>
```

If you did not follow the steps to alias the `python` and `pip` commands, you can use the following command to check which version of python `python3` is aliased to:

```bash
which python3
```

If `python3` is aliased to `python3.12` then you can use the following command:

```bash
python3 -m venv <env_name>
```

If `python3` is not aliased to `python3.12` first check if `python3.12` is installed:

```bash
which python3.12
```

If it is not installed please return to the [Installation by Operating System](#installation-by-operating-system) section and follow the instructions for your operating system to install Python 3.12.

If `python3.12` is installed, but isn't aliased to `python3`, then you can instead use this command:

```bash
python3.12 -m venv <env_name>
```

</br>

#### 2. Activate the environment

**Windows (Command Prompt)**:

```bash
<env_name>\Scripts\activate
```

**Windows (PowerShell)**:

```bash
<env_name>\Scripts\Activate.ps1
```

**macOS/Linux**:

```bash
source <env_name>/bin/activate
```

</br>

### Using Conda (Recommended)

#### 1. Install Miniconda

> [!NOTE]  
> For all systems, you can use install Miniconda from the [Conda Downloads](https://www.anaconda.com/download/) page, for macOS/Linux there's a slightly more streamlined process using `curl` to download and install Miniconda, details are below.

**Windows**:

- Download and run the installer from [Conda Downloads](https://www.anaconda.com/download/)

</br>

Below are the alternatives for macOS and Linux using `curl`.

**macOS Intel**:

```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh
```

**macOS Apple Silicon (M1/M2)**:

```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh
```

**Linux**:

```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

#### 2. Create a new environment

```bash
conda create -n <env_name> python=3.12
```

#### 3. Activate the environment

```bash
conda activate <env_name>
```

</br>

## Troubleshooting

### Common Issues

#### 1. Python not found in PATH

- **Windows**: Reinstall with "Add to PATH" checked

- **macOS/Linux**: Add to shell profile:

    **For Zsh**:

    ```bash
    echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
    ```

    **For Bash**:

    ```bash
    echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
    ```

#### 2. Permission Issues

- **Windows**: Run installer as Administrator

- **macOS/Linux**: Use `sudo` for system-wide installation

- **Virtual Environments**: Avoid using `sudo`

#### 3. Multiple Python Versions

- Use virtual environments (recommended)

- Specify version explicitly: `python3.12` instead of `python`

- Check active version:
  - `which python` or `where python` (Windows)
  - `which python3` or `where python3` (macOS/Linux)

</br>

> [!TIP]  
> **Aliasing the `python` and `pip` commands**
>
> For **macOS/Linux** If you'd like to be able to use `python` instead of `python3`/`python3.12`, you can add the following to your shell profile:
>
> ```bash
> alias python=python3.12
> alias pip="python3.12 -m pip"
> ```
>
> To do so run the following command:
>
> **Zsh**:
>
> ```bash
> echo 'alias python=python3.12' >> ~/.zshrc
> echo 'alias pip="python3.12 -m pip"' >> ~/.zshrc
> source ~/.zshrc
> ```
>
> **Bash**:
>
> ```bash
> echo 'alias python=python3.12' >> ~/.bashrc
> echo 'alias pip="python3.12 -m pip"' >> ~/.bashrc
> source ~/.bashrc
> ```
>
> Then when installing packages and running scripts instead of:
>
> **Zsh**:
>
> ```bash
> pip3.12 install package_name
> python3.12 script.py
> ```
>
> **Bash**:
>
> ```bash
> pip3 install package_name
> python3 script.py
> ```
>
> You can simply use:
>
> ```bash
> pip install package_name
> python script.py
> ```
>
> If at a later date you'd like to revert back you can simply remove the alias by running the following command:
>
> **Zsh**:
>
> ```bash
> unalias python
> unalias pip
> ```
>
> **Bash**:
>
> ```bash
> unalias python
> unalias pip
> ```
>
> or if you'd like to change which version of python and pip you're using you can simply change the alias to the version you'd like to use. You can change the alias to the version you'd like to use by running the following command:
>
> **Zsh**:
>
> ```bash
> alias python=python3.x
> alias pip="python3.x -m pip"
> ```
>
> **Bash**:
>
> ```bash
> alias python=python3.x
> alias pip="python3.x -m pip"
> ```
>
> Where `x` is the version extension you'd like to use, such as `3.12`, `3.11`, `3.9`, etc.

</br>

## Package Management

### Using pip (Python Package Installer)

```bash
# Install a package
pip install package_name

# Install specific version
pip install package_name==1.2.3

# Install from requirements.txt
pip install -r requirements.txt

# List installed packages
pip list
```

</br>

## Additional Resources

- [Official Python Documentation](https://docs.python.org/3.12/)
- [Python Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)
- [pip Documentation](https://pip.pypa.io/en/stable/)

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Consult the official documentation
3. Search for similar issues on Stack Overflow
4. Ensure you're using the correct Python version
5. Verify your virtual environment is activated if using one
6. If all else fails, feel free to contact me, you can find my contact information in the [Wrapping Up](../../README.md#wrapping-up) section of the [README.md](../../README.md) file.
