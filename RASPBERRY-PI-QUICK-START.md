# 🍓 Raspberry Pi Quick Start Guide

## 🚀 One-Command Deployment

```bash
# Basic deployment (recommended for most users)
./scripts/deploy.sh -e raspberry-pi deploy

# With monitoring dashboard
./scripts/deploy.sh -e raspberry-pi -p monitoring deploy

# Full deployment with reverse proxy
./scripts/deploy.sh -e raspberry-pi -p nginx,monitoring deploy
```

## 🔧 Network Mode Fix

The Raspberry Pi configuration (`docker-compose.rpi.yml`) resolves the common Docker networking conflict:

### ❌ Problem (Standard Config)
```yaml
services:
  app:
    network_mode: host    # Uses host network
    ports:
      - "5000:5000"      # ❌ CONFLICT! Can't map ports with host network
```

### ✅ Solution (RPi Config)
```yaml
services:
  app:
    network_mode: host    # Uses host network
    # NO ports declaration - app binds directly to host:5000
    environment:
      - APP_PORT=5000     # App binds to this port on host
```

## 📋 Quick Commands

```bash
# Deploy
./scripts/deploy.sh -e raspberry-pi deploy

# Check status
./scripts/deploy.sh -e raspberry-pi status

# View logs
./scripts/deploy.sh -e raspberry-pi logs

# Restart
./scripts/deploy.sh -e raspberry-pi restart

# Stop
./scripts/deploy.sh -e raspberry-pi stop

# Validate configuration
python scripts/validate-docker-config.py docker-compose.rpi.yml
```

## 🌐 Access Points

After deployment, access your application at:

- **Main App**: `http://raspberry-pi-ip:5000`
- **Health Check**: `http://raspberry-pi-ip:5000/health`
- **Prometheus** (if monitoring enabled): `http://raspberry-pi-ip:9090`
- **Grafana** (if monitoring enabled): `http://raspberry-pi-ip:3000`

## 🔍 Troubleshooting

### Check if app is running
```bash
curl http://localhost:5000/health
```

### Check Docker containers
```bash
docker ps
```

### Check port usage
```bash
sudo netstat -tulpn | grep :5000
```

### View application logs
```bash
docker logs rogue-garmin-bridge-rpi
```

## 📊 Resource Usage

The RPi configuration is optimized for Raspberry Pi 4 with 4GB+ RAM:

- **Main App**: 256MB RAM, 0.8 CPU cores
- **Nginx**: 64MB RAM, 0.2 CPU cores  
- **Prometheus**: 128MB RAM, 0.3 CPU cores
- **Grafana**: 128MB RAM, 0.3 CPU cores

Total: ~576MB RAM when all services are running.

## 🔒 Security

The configuration includes:
- Non-root user execution
- Resource limits to prevent resource exhaustion
- Proper volume permissions
- Health checks for service monitoring

For production use, consider:
- Setting up SSL certificates
- Configuring firewall rules
- Using strong passwords
- Regular security updates