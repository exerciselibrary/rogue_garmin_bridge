# Raspberry Pi Deployment Guide

This guide covers deploying the Rogue Garmin Bridge application on Raspberry Pi with proper Docker networking configuration.

## 🔧 Network Mode Issue Resolution

### The Problem
When deploying to Raspberry Pi, you may encounter conflicts between:
- `network_mode: host` (required for Bluetooth access)
- `ports:` declarations (incompatible with host networking)

### The Solution
The `docker-compose.rpi.yml` configuration resolves this by:
- Using `network_mode: host` for the main application (no port mappings)
- Using bridge networking for auxiliary services (nginx, monitoring)
- Connecting services via `host.docker.internal`

## 🚀 Quick Start

### 1. Prepare Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Reboot to apply group changes
sudo reboot
```

### 2. Clone and Configure
```bash
# Clone repository
git clone <repository-url>
cd rogue-garmin-bridge

# Copy and customize Raspberry Pi environment
cp .env.rpi .env.rpi.local
nano .env.rpi.local  # Edit with your settings
```

### 3. Deploy
```bash
# Deploy basic application
./scripts/deploy.sh -e raspberry-pi deploy

# Deploy with monitoring
./scripts/deploy.sh -e raspberry-pi -p monitoring deploy

# Deploy with nginx reverse proxy
./scripts/deploy.sh -e raspberry-pi -p nginx deploy
```

## 📋 Prerequisites

### Hardware Requirements
- **Raspberry Pi 4** (recommended) or Pi 3B+
- **4GB RAM minimum** (8GB recommended for monitoring)
- **32GB+ SD card** (Class 10 or better)
- **Bluetooth adapter** (built-in or USB)

### Software Requirements
- **Raspberry Pi OS** (64-bit recommended)
- **Docker** 20.10+
- **Docker Compose** 2.0+

## 🔧 Configuration

### Environment Variables (.env.rpi)
Key settings optimized for Raspberry Pi:

```bash
# Performance optimized for RPi
DATA_RETENTION_DAYS=90      # Reduced storage usage
MAX_FIT_FILE_AGE_DAYS=14    # Reduced storage usage
API_RATE_LIMIT=50 per minute # Reduced for RPi performance

# Application port (accessible via host network)
APP_PORT=5000
```

### Resource Limits
The RPi configuration includes optimized resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 256M  # Reduced for RPi
      cpus: '0.8'   # Reduced for RPi
    reservations:
      memory: 128M
      cpus: '0.4'
```

## 🌐 Networking Architecture

### Host Network Mode (Main App)
```
┌─────────────────────────────────────┐
│           Raspberry Pi Host         │
│  ┌─────────────────────────────────┐│
│  │     Docker Container            ││
│  │   (network_mode: host)          ││
│  │                                 ││
│  │  App binds to: localhost:5000   ││
│  │  Bluetooth: Direct host access  ││
│  └─────────────────────────────────┘│
│                                     │
│  Accessible at: http://rpi-ip:5000  │
└─────────────────────────────────────┘
```

### Bridge Network Mode (Auxiliary Services)
```
┌─────────────────────────────────────┐
│           Raspberry Pi Host         │
│  ┌─────────────────────────────────┐│
│  │        Docker Bridge            ││
│  │                                 ││
│  │  ┌─────────┐    ┌─────────────┐ ││
│  │  │  Nginx  │    │ Prometheus  │ ││
│  │  │ :80:443 │    │    :9090    │ ││
│  │  └─────────┘    └─────────────┘ ││
│  │       │               │        ││
│  │       └───────────────┼────────┘│
│  │                       │         │
│  │  Connect to main app via:       │
│  │  host.docker.internal:5000      │
└─────────────────────────────────────┘
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Port Conflicts
**Error**: `Port already in use` or `Cannot assign requested address`

**Solution**: Check if services are already running on the host:
```bash
# Check what's using port 5000
sudo netstat -tulpn | grep :5000

# Stop conflicting services
sudo systemctl stop <service-name>
```

#### 2. Bluetooth Access Issues
**Error**: `Permission denied` or `Bluetooth adapter not found`

**Solution**: Ensure proper permissions and privileges:
```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# Add user to bluetooth group
sudo usermod -aG bluetooth $USER

# Verify container has privileged access
docker-compose -f docker-compose.rpi.yml ps
```

#### 3. Memory Issues
**Error**: Container killed due to OOM (Out of Memory)

**Solution**: Optimize memory usage:
```bash
# Check memory usage
free -h
docker stats

# Reduce resource limits in docker-compose.rpi.yml
# Disable unnecessary services/profiles
```

#### 4. Storage Issues
**Error**: `No space left on device`

**Solution**: Manage storage:
```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a

# Reduce data retention in .env.rpi
DATA_RETENTION_DAYS=30
MAX_FIT_FILE_AGE_DAYS=7
```

### Network Debugging

#### Test Host Network Access
```bash
# From inside the container
docker exec -it rogue-garmin-bridge-rpi curl http://localhost:5000/health

# From host
curl http://localhost:5000/health

# From another machine
curl http://raspberry-pi-ip:5000/health
```

#### Test Bridge Network Communication
```bash
# Test nginx to app communication
docker exec -it rogue-garmin-bridge-nginx-rpi curl http://host.docker.internal:5000/health

# Test prometheus to app communication
docker exec -it rogue-garmin-bridge-prometheus-rpi wget -qO- http://host.docker.internal:5000/metrics
```

## 🔒 Security Considerations

### Firewall Configuration
```bash
# Install UFW if not present
sudo apt install ufw

# Allow SSH
sudo ufw allow ssh

# Allow application port
sudo ufw allow 5000/tcp

# Allow HTTP/HTTPS (if using nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow monitoring (if using monitoring profile)
sudo ufw allow 9090/tcp  # Prometheus
sudo ufw allow 3000/tcp  # Grafana

# Enable firewall
sudo ufw enable
```

### SSL/TLS Setup
For production deployment with nginx:

```bash
# Generate self-signed certificate
sudo mkdir -p nginx/ssl
sudo openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes

# Or use Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
```

## 📊 Monitoring

### Resource Monitoring
```bash
# System resources
htop

# Docker resources
docker stats

# Application logs
./scripts/deploy.sh -e raspberry-pi logs

# System logs
journalctl -u docker -f
```

### Performance Optimization

#### 1. SD Card Optimization
```bash
# Move logs to tmpfs (RAM)
echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0" | sudo tee -a /etc/fstab
echo "tmpfs /var/log tmpfs defaults,noatime,nosuid,mode=0755,size=100m 0 0" | sudo tee -a /etc/fstab
```

#### 2. Docker Optimization
```bash
# Configure Docker daemon for RPi
sudo tee /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

## 🚀 Deployment Profiles

### Basic Deployment
```bash
./scripts/deploy.sh -e raspberry-pi deploy
```
- Main application only
- Minimal resource usage
- Direct access via port 5000

### With Reverse Proxy
```bash
./scripts/deploy.sh -e raspberry-pi -p nginx deploy
```
- Nginx reverse proxy
- SSL termination
- Access via ports 80/443

### With Monitoring
```bash
./scripts/deploy.sh -e raspberry-pi -p monitoring deploy
```
- Prometheus metrics collection
- Grafana dashboards
- System monitoring

### Full Deployment
```bash
./scripts/deploy.sh -e raspberry-pi -p nginx,monitoring,logging deploy
```
- All services enabled
- Complete monitoring stack
- Log management

## 📝 Maintenance

### Regular Tasks
```bash
# Update application
./scripts/deploy.sh -e raspberry-pi update

# View logs
./scripts/deploy.sh -e raspberry-pi logs

# Check status
./scripts/deploy.sh -e raspberry-pi status

# Backup data
./scripts/deploy.sh -e raspberry-pi backup

# Clean up resources
./scripts/deploy.sh -e raspberry-pi cleanup
```

### System Maintenance
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose -f docker-compose.rpi.yml pull

# Clean Docker resources
docker system prune -a

# Check disk space
df -h
du -sh data/ logs/ fit_files/
```

## 🆘 Support

### Getting Help
1. Check application health: `curl http://localhost:5000/health/detailed`
2. Review logs: `./scripts/deploy.sh -e raspberry-pi logs`
3. Check system resources: `htop` and `docker stats`
4. Verify network connectivity: Test port access from other devices

### Common Commands
```bash
# Quick status check
./scripts/deploy.sh -e raspberry-pi status

# Restart services
./scripts/deploy.sh -e raspberry-pi restart

# View real-time logs
./scripts/deploy.sh -e raspberry-pi logs

# Emergency stop
./scripts/deploy.sh -e raspberry-pi stop
```

This Raspberry Pi deployment configuration resolves the network mode conflicts while maintaining full Bluetooth functionality and providing optimized performance for ARM architecture.