FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install zsh, curl, git, and other needed packages
RUN apt-get update && apt-get install -y \
    zsh \
    vim \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set zsh as the default shell
SHELL ["/bin/zsh", "-c"]

# Default command to run when starting the container
CMD ["zsh"]