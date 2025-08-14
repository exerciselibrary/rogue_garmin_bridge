# Installation Guide

This guide provides step-by-step installation instructions for the Rogue Garmin Bridge application on all supported platforms.

## System Requirements

### Minimum Requirements
- **Python**: 3.12 or higher (required for `pyftms` library)
- **RAM**: 512MB available memory
- **Storage**: 100MB free disk space
- **Bluetooth**: BLE-compatible Bluetooth adapter
- **Network**: Internet connection for Garmin Connect integration

### Supported Operating Systems
- Windows 10/11 (64-bit)
- macOS 10.15 (Catalina) or later
- Linux (Ubuntu 20.04+, Debian 10+, Raspberry Pi OS)

### Compatible Equipment
- Rogue Echo Bike (with FTMS support)
- Rogue Echo Rower (with FTMS support)

## Pre-Installation Setup

### Windows Setup

1. **Install Python 3.12**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"
   - Verify installation: Open Command Prompt and run `python --version`

2. **Bluetooth Setup**
   - Ensure Bluetooth is enabled in Windows Settings
   - Update Bluetooth drivers if needed
   - Verify BLE support in Device Manager

3. **Install Git (Optional)**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Use default installation options

### macOS Setup

1. **Install Python 3.12**
   - Option 1: Download from [python.org](https://www.python.org/downloads/)
   - Option 2: Use Homebrew: `brew install python@3.12`
   - Verify installation: `python3.12 --version`

2. **Bluetooth Setup**
   - Bluetooth is built-in on modern Macs
   - Ensure Bluetooth is enabled in System Preferences

3. **Install Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

### Linux Setup

1. **Install Python 3.12**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.12 python3.12-venv python3.12-pip
   
   # CentOS/RHEL/Fedora
   sudo dnf install python3.12 python3.12-pip
   ```

2. **Install Bluetooth Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt install bluetooth bluez libbluetooth-dev
   
   # CentOS/RHEL/Fedora
   sudo dnf install bluez bluez-libs-devel
   ```

3. **Configure Bluetooth Permissions**
   ```bash
   # Add user to bluetooth group
   sudo usermod -a -G bluetooth $USER
   
   # Enable and start Bluetooth service
   sudo systemctl enable bluetooth
   sudo systemctl start bluetooth
   ```

### Raspberry Pi Setup

1. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python 3.12**
   ```bash
   sudo apt install python3.12 python3.12-venv python3.12-pip
   ```

3. **Enable Bluetooth**
   ```bash
   sudo systemctl enable bluetooth
   sudo systemctl start bluetooth
   ```

## Installation Methods

### Method 1: Git Clone (Recommended)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Douglas-Christian/rogue_garmin_bridge.git
   cd rogue_garmin_bridge
   ```

2. **Create Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: Download ZIP

1. **Download and Extract**
   - Download ZIP from GitHub repository
   - Extract to desired location
   - Open terminal/command prompt in extracted folder

2. **Follow steps 2-3 from Method 1**

## Post-Installation Configuration

### 1. Verify Installation

```bash
# Test Python installation
python --version  # Should show 3.12+

# Test application startup
python src/web/app.py --help
```

### 2. Initial Configuration

1. **Start the Application**
   ```bash
   python src/web/app.py
   ```

2. **Access Web Interface**
   - Open browser to `http://localhost:5000`
   - Complete initial setup wizard

3. **Configure User Profile**
   - Navigate to Settings page
   - Enter personal information and preferences
   - Set unit preferences (metric/imperial)

### 3. Device Setup

1. **Prepare Your Equipment**
   - **Echo Bike**: Press and hold "Connect" button for 2 seconds
   - **Echo Rower**: Select "Connect" → "Connect to App" from menu

2. **Pair Device**
   - Navigate to Devices page in web interface
   - Click "Discover Devices"
   - Select your equipment from the list
   - Follow pairing wizard instructions

## Troubleshooting Installation Issues

### Python Version Issues

**Problem**: `pyftms` requires Python 3.12+
**Solution**: 
```bash
# Check Python version
python --version

# If version is too old, install Python 3.12
# Follow platform-specific instructions above
```

### Bluetooth Permission Issues (Linux)

**Problem**: Permission denied accessing Bluetooth
**Solution**:
```bash
# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER

# Logout and login again, or restart
```

### Virtual Environment Issues

**Problem**: Virtual environment activation fails
**Solution**:
```bash
# Recreate virtual environment
rm -rf venv
python3.12 -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Dependency Installation Issues

**Problem**: Package installation fails
**Solution**:
```bash
# Update pip
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Try installing packages individually
pip install flask pyftms bleak
```

### Port Already in Use

**Problem**: Port 5000 already in use
**Solution**:
```bash
# Use different port
python src/web/app.py --port 5001

# Or set environment variable
export PORT=5001
python src/web/app.py
```

## Advanced Installation Options

### Docker Installation

1. **Install Docker**
   - Follow Docker installation guide for your platform

2. **Build and Run**
   ```bash
   docker build -t rogue-garmin-bridge .
   docker run -p 5000:5000 --privileged rogue-garmin-bridge
   ```

### Development Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/Douglas-Christian/rogue_garmin_bridge.git
   cd rogue_garmin_bridge
   ```

2. **Install Development Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

### Production Installation

1. **Use Production Configuration**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key-here
   ```

2. **Use Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 src.web.app:app
   ```

## Next Steps

After successful installation:

1. **Read the User Manual**: `docs/user-guide/user-manual.md`
2. **Complete Device Setup**: Follow device pairing instructions
3. **Start Your First Workout**: Use the workout monitoring features
4. **Explore Advanced Features**: Settings, history, and analytics

## Getting Help

If you encounter issues during installation:

1. **Check Troubleshooting Guide**: `docs/user-guide/troubleshooting.md`
2. **Review System Requirements**: Ensure all prerequisites are met
3. **Check Application Logs**: Located in `logs/` directory
4. **Use Built-in Diagnostics**: Available in web interface
5. **Submit Issue**: Create GitHub issue with detailed error information

## Uninstallation

To remove the application:

1. **Deactivate Virtual Environment**
   ```bash
   deactivate
   ```

2. **Remove Application Directory**
   ```bash
   rm -rf rogue_garmin_bridge
   ```

3. **Remove Python (Optional)**
   - Follow platform-specific Python removal instructions
   - Only if Python was installed specifically for this application