# MongoDB Installation Guide

## Introduction

MongoDB is a popular NoSQL database that stores data in flexible, [_JSON-like_](https://www.json.org/json-en.html) [_documents_](https://www.mongodb.com/docs/manual/core/document/). This guide will walk you through:

- Installing MongoDB locally on your machine
- Setting up MongoDB Atlas (cloud version)
- Basic operations and commands
- Troubleshooting common issues

## Table of Contents

- [MongoDB Installation Guide](#mongodb-installation-guide)
  - [Introduction](#introduction)
  - [Table of Contents](#table-of-contents)
  - [Local Installation](#local-installation)
    - [Windows Installation](#windows-installation)
    - [macOS Installation](#macos-installation)
    - [Linux Installation](#linux-installation)
  - [MongoDB Atlas Setup](#mongodb-atlas-setup)
    - [Creating an Account](#creating-an-account)
    - [Setting up a Cluster](#setting-up-a-cluster)
    - [Getting Connection String](#getting-connection-string)
  - [Basic Operations](#basic-operations)
    - [Starting MongoDB](#starting-mongodb)
    - [Using mongosh](#using-mongosh)
    - [Creating Databases](#creating-databases)
    - [Basic Commands](#basic-commands)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Security Considerations](#security-considerations)
  - [Additional Resources](#additional-resources)

## Local Installation

### Windows Installation

1. **Download MongoDB Community Server**

   - Visit [MongoDB Download Center](https://www.mongodb.com/try/download/community)
   - Select "Windows" as your platform
   - Choose "msi" as the package
   - Click "Download"

2. **Run the Installer**

   - Double-click the downloaded .msi file
   - Choose "Complete" installation
   - ✅ Check "Install MongoDB as a Service"
   - Click "Install"

3. **Start MongoDB**

    ```bash
    # Check if MongoDB is running
    net start MongoDB
    ```

    - If you see "The MongoDB Server service is starting.", wait a moment.

    - If you see "The MongoDB Server service was started successfully.", you're ready to go.

    - If you see "The MongoDB Server service is not started.", run:

        ```bash
        net start MongoDB
        ```

4. **Verify Installation and Connection**

    ```bash
    # Try to connect to MongoDB
    mongosh
    ```

    You should see something like:

    ```bash
    Current Mongosh Log ID: ...
    Connecting to: mongodb://127.0.0.1:27017...
    Using MongoDB: x.x.x
    ```

### macOS Installation

1. **Using Homebrew (Recommended)**

    ```bash
    # Check if Homebrew is installed
    brew --version
    
    # Install Homebrew if not already installed
    #
    #
    # Bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    #
    #
    # Zsh
    /bin/zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # If Homebrew is already installed, check if MongoDB is installed
    brew list | grep mongodb-community

    # If MongoDB is already installed, check if it is running
    brew services list | grep mongodb-community

    # If MongoDB is not installed, install it
    brew tap mongodb/brew
    brew install mongodb-community

    # If you just installed MongoDB, or it wasn't running, start it
    brew services start mongodb-community
    ```

2. **Verify Installation and Connection**

   ```bash
   # Try to connect to MongoDB
   mongosh
   ```

### Linux Installation

1. **Ubuntu/Debian**

    ```bash
    # Check if MongoDB is installed
    sudo apt-get install -y mongodb-org

    # If MongoDB is already installed, check if it is running
    sudo systemctl status mongod

    # If MongoDB installed but not running, start it
    sudo systemctl start mongod

    # If MongoDB is not installed, install it
    #
    #
    # Import MongoDB public key
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
    sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
    --dearmor

    # Create list file
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
    sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
   
    # Update package list
    sudo apt-get update

    # Install MongoDB
    sudo apt-get install -y mongodb-org

    # Start MongoDB
    sudo systemctl start mongod
    ```

2. **Verify Installation and Connection**

    ```bash
    # Try to connect to MongoDB
    mongosh
    ```

## MongoDB Atlas Setup

### Creating an Account

1. Visit [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)

2. Sign up for a free account

3. Choose the free tier option ("Shared" cluster)

### Setting up a Cluster

1. Choose your preferred cloud provider (AWS, Google Cloud, or Azure)

2. Select a region closest to you

3. Choose "M0 Sandbox" (free tier)

4. Click "Create Cluster"

### Getting Connection String

1. Click "Connect" on your cluster

2. Choose "Connect your application"

3. Select your driver and version

4. Copy the connection string

5. Replace `<password>` with your database user password

## Basic Operations

### Starting MongoDB

If for whatever reason you still need to start MongoDB, this section will provide you with the commands to do so.

**Windows**:

```bash
# MongoDB should start automatically as a service
# To start manually:
net start MongoDB
```

**macOS**:

```bash
brew services start mongodb-community
```

**Linux**:

```bash
sudo systemctl start mongod
```

### Using mongosh

Connect to MongoDB:

```bash
mongosh
```

### Creating Databases

```bash
# List existing databases
show dbs

# Create/switch to a database
use your_database_name

# The database won't appear in show dbs until you add data.
#
# The system will automatically add data to the database, but if you'd like to verify it was created 
# you can add data to it, then check it by running `show dbs` again.
db.createCollection("your_collection_name")
```

### Basic Commands

```bash
# Show current database
db

# Show collections
show collections

# Insert a document
db.your_collection_name.insertOne({ name: "test" })

# Find documents
db.your_collection_name.find()
```

## Troubleshooting

### Common Issues

1. **Connection Refused**

   - Check if MongoDB is running:

     ```bash
     # Windows
     net start MongoDB
     
     # macOS
     brew services list
     
     # Linux
     sudo systemctl status mongod
     ```

2. **Permission Issues**

   - Ensure proper directory permissions:

     ```bash
     # Linux/macOS
     sudo chown -R `id -un` /data/db
     ```

3. **Port Already in Use**

   - Check if another process is using port 27017:

     ```bash
     # Windows
     netstat -ano | findstr 27017
     
     # Linux/macOS
     lsof -i :27017
     ```

### Security Considerations

1. **Enable Authentication (Optional)**

    If for whatever reason you need added security for your MongoDB instance, you can conduct the following to add authentication to your database:

    ```bash
    use admin
    db.createUser({
        user: "adminUser",
        pwd: "securePassword",
        roles: ["userAdminAnyDatabase"]
    })
    ```

2. **Firewall Settings**

   - Allow port 27017 for MongoDB
   - Restrict access to trusted IP addresses

## Additional Resources

- [MongoDB Documentation](https://www.mongodb.com/docs/)
- [MongoDB University](https://university.mongodb.com/) (free courses)
- [MongoDB Community Forums](https://www.mongodb.com/community/forums/)
