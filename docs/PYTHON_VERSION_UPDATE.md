# Python Version Update Guide

This document explains how to update your virtual environment after upgrading the Python version from 3.9 to 3.11.

## Overview

The project has been upgraded from Python 3.9 to Python 3.11. This requires recreating your virtual environment with the new Python version.

## Method 1: Using Pipenv (Recommended)

Pipenv will automatically recreate the virtual environment with the new Python version.

### Step 1: Remove the old virtual environment

```bash
pipenv --rm
```

This removes the existing virtual environment that was created with Python 3.9.

### Step 2: Recreate with Python 3.11

```bash
# If you have Python 3.11 installed as 'python3.11'
pipenv --python 3.11

# Or if Python 3.11 is your default python3
pipenv --python $(which python3)

# Or specify the full path
pipenv --python /usr/bin/python3.11
```

### Step 3: Install dependencies

```bash
pipenv install --dev
```

### Step 4: Verify the Python version

```bash
pipenv run python --version
```

Should output: `Python 3.11.x`

## Method 2: Manual venv Recreation

If you're using standard venv instead of pipenv:

### Step 1: Remove the old venv

```bash
# If your venv is in the project directory
rm -rf venv/

# Or wherever your venv is located
rm -rf ~/.virtualenvs/zotero-substack-fix/
```

### Step 2: Create new venv with Python 3.11

```bash
python3.11 -m venv venv
```

### Step 3: Activate and install dependencies

```bash
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt  # If you have requirements.txt
# or install from Pipfile
pip install pyzotero python-dotenv requests python-dateutil extruct w3lib backoff websockets beautifulsoup4
```

## Method 3: Using pyenv (For Multiple Python Versions)

If you need to manage multiple Python versions:

### Step 1: Install Python 3.11 with pyenv

```bash
pyenv install 3.11.7  # Or latest 3.11.x version
pyenv local 3.11.7
```

### Step 2: Recreate pipenv environment

```bash
pipenv --rm
pipenv --python 3.11
pipenv install --dev
```

## Verifying the Installation

After recreating your environment, verify everything works:

```bash
# Check Python version
pipenv run python --version

# Run tests
pipenv run python tests/test_real_urls.py

# Check that all dependencies are installed
pipenv run python -c "import bs4, requests, pyzotero; print('All imports successful')"
```

## Troubleshooting

### Issue: Python 3.11 not found

**Solution**: Install Python 3.11 first:

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# On macOS with Homebrew
brew install python@3.11

# On macOS with pyenv
pyenv install 3.11.7
```

### Issue: pipenv uses wrong Python version

**Solution**: Specify the exact Python executable:

```bash
pipenv --python /usr/bin/python3.11
# or
pipenv --python $(which python3.11)
```

### Issue: "Pipfile requires python_version 3.11 but you are using 3.9"

**Solution**: This means you're still using the old venv. Follow Method 1 above to recreate it.

### Issue: Dependencies fail to install

**Solution**: Make sure you have system dependencies installed:

```bash
# On Ubuntu/Debian
sudo apt install python3.11-dev build-essential

# On macOS
xcode-select --install
```

## Why Upgrade to Python 3.11?

- **Better Performance**: Python 3.11 is significantly faster (10-60% in many cases)
- **Better Error Messages**: More helpful error messages and tracebacks
- **Security**: Python 3.9 will reach end-of-life in October 2025
- **Modern Features**: Access to newer language features and standard library improvements

## Compatibility Notes

All dependencies used in this project are compatible with Python 3.11:
- ✅ pyzotero
- ✅ python-dotenv
- ✅ requests
- ✅ python-dateutil
- ✅ extruct
- ✅ w3lib
- ✅ backoff
- ✅ websockets
- ✅ beautifulsoup4

## Quick Reference

```bash
# Complete update process (recommended)
pipenv --rm                    # Remove old venv
pipenv --python 3.11           # Create new venv with Python 3.11
pipenv install --dev           # Install all dependencies
pipenv run python --version    # Verify version
pipenv run python tests/test_real_urls.py  # Test everything works
```

That's it! Your environment is now updated to Python 3.11.
