# Updated config.md

# Rogue to Garmin Bridge - Deployment Configuration

This file contains configuration for deploying the Rogue to Garmin Bridge application to various cloud platforms or local environments.

## Environment Variables

The following environment variables can be set to configure the application:

* `PORT`: The port to run the application on (default: 5000)
* `DEBUG`: Set to "True" to enable debug mode (default: False)
* `DATABASE_URL`: URL for the database (default: SQLite database in the data directory)
* `SECRET_KEY`: Secret key for session encryption (required for production)

## Docker Deployment

The project includes a Dockerfile for containerized deployment. To build and run the Docker container:

```bash
# Build the Docker image
docker build -t rogue-garmin-bridge .

# Run the container
docker run -p 5000:5000 -e SECRET_KEY=your_secret_key rogue-garmin-bridge
```

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
