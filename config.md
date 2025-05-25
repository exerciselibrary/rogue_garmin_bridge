# Updated config.md with Raspberry Pi Docker Deployment

# Rogue to Garmin Bridge - Deployment Configuration

This file contains configuration for deploying the Rogue to Garmin Bridge application to various cloud platforms or local environments.

## Environment Variables

The following environment variables can be set to configure the application:

* `PORT`: The port to run the application on (default: 5000)
* `DEBUG`: Set to "True" to enable debug mode (default: False)
* `DATABASE_URL`: URL for the database (default: SQLite database in the data directory)
* `SECRET_KEY`: Secret key for session encryption (required for production)
* `USE_SIMULATOR`: Set to "True" to enable the FTMS device simulator (default: False)

## Docker Deployment

The project includes a Dockerfile for containerized deployment. 

### Basic Docker Deployment

```bash
# Build the Docker image
docker build -t rogue-garmin-bridge .

# Run the container
docker run -p 5000:5000 -e SECRET_KEY=your_secret_key rogue-garmin-bridge
```

### Raspberry Pi Docker Deployment

Follow these steps to deploy the application on a Raspberry Pi using Docker:

#### 1. Install Docker on Raspberry Pi

```bash
# Update your system
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/raspbian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the stable repository
echo "deb [arch=armhf signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/raspbian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add your user to the docker group to run Docker without sudo
sudo usermod -aG docker $USER

# Enable Docker to start on boot
sudo systemctl enable docker
```

You'll need to log out and log back in for the group changes to take effect, or you can run:

```bash
newgrp docker
```

#### 2. Install Docker Compose (Optional but Recommended)

```bash
sudo apt-get install -y python3-pip
sudo pip3 install docker-compose
```

#### 3. Configure Bluetooth for Docker

Since this application requires Bluetooth access, you need to configure Docker to access the Bluetooth hardware:

```bash
# Install Bluetooth packages
sudo apt-get install -y bluez bluez-tools

# Ensure Bluetooth service is running
sudo systemctl start bluetooth
sudo systemctl enable bluetooth

# Add your user to the bluetooth group
sudo usermod -aG bluetooth $USER
```

#### 4. Build the Docker Image

```bash
# Navigate to the project directory
cd /path/to/rogue_garmin_bridge

# Build the Docker image
docker build -t rogue-garmin-bridge .
```

#### 5. Run the Docker Container with Bluetooth Support

```bash
docker run -d \
  --name rogue-garmin-bridge \
  --restart unless-stopped \
  --net=host \
  --privileged \
  -v /var/run/dbus:/var/run/dbus \
  -v /var/run/bluetooth:/var/run/bluetooth \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/fit_files:/app/fit_files \
  -e PORT=5000 \
  -e SECRET_KEY=your_secret_key_here \
  -e DEBUG=False \
  rogue-garmin-bridge
```

Notes:
- `--net=host` gives the container access to the host's network
- `--privileged` and the volume mounts give access to Bluetooth
- Replace `your_secret_key_here` with a secure random string
- The `-v` options create persistent storage for data and FIT files

#### 6. Run with Simulator (No Physical Hardware)

If you don't have physical Rogue equipment available, you can run with the simulator:

```bash
docker run -d \
  --name rogue-garmin-bridge \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/fit_files:/app/fit_files \
  -e PORT=5000 \
  -e SECRET_KEY=your_secret_key_here \
  -e DEBUG=False \
  -e USE_SIMULATOR=True \
  rogue-garmin-bridge
```

### Docker Troubleshooting

#### Permission Denied Error

If you encounter this error:
```
ERROR: permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Head "http://%2Fvar%2Frun%2Fdocker.sock/_ping": dial unix /var/run/docker.sock: connect: permission denied
```

There are two ways to fix this:

**Option 1: Use sudo (Immediate Solution)**
```bash
sudo docker build -t rogue-garmin-bridge .
sudo docker run ...
```

**Option 2: Add Your User to the Docker Group (Recommended)**
```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Apply the new group membership
newgrp docker
# Or log out and log back in

# Verify that you can run Docker commands without sudo
docker ps
```

#### Bluetooth Connectivity Issues

If you encounter Bluetooth connectivity issues:
1. Ensure the Bluetooth service is running on the host: `sudo systemctl status bluetooth`
2. Check if your Bluetooth adapter is recognized: `hcitool dev`
3. Restart the Bluetooth service: `sudo systemctl restart bluetooth`
4. Restart the container: `docker restart rogue-garmin-bridge`

## Platform-Specific Deployment Notes

### Linux

When deploying on Linux systems, ensure that the `bluez` package is installed for proper Bluetooth functionality:

```bash
sudo apt-get update
sudo apt-get install bluez bluez-tools
```

### Raspberry Pi

The application is compatible with Raspberry Pi devices, which can serve as an always-on bridge between your Rogue equipment and Garmin Connect. Ensure you're using Python 3.12+ and have the necessary Bluetooth permissions:

```bash
sudo usermod -a -G bluetooth $USER
```

### Cloud Deployment

When deploying to cloud platforms, note that Bluetooth functionality will not be available. The application can still be used with the simulator for demonstration purposes by setting:

```
--use-simulator
```

## Python Version Requirements

This application requires Python 3.12 or higher due to dependencies in the `pyftms` library. Ensure you're using the correct Python version when deploying:

```bash
python3.12 src/web/app.py
```
