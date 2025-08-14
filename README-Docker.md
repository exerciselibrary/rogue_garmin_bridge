# Docker Deployment - Rogue Garmin Bridge

This document provides comprehensive instructions for deploying the Rogue Garmin Bridge application using Docker across different environments.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd rogue-garmin-bridge

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Deploy
./scripts/deploy.sh deploy
```

## 📋 Prerequisites

- **Docker Engine**: 20.10 or later
- **Docker Compose**: 2.0 or later
- **Python 3**: For configuration validation
- **curl**: For health checks
- **Git**: For repository management

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Application   │    │   Monitoring    │
│   (Optional)    │────│   Container     │────│   Stack         │
│                 │    │                 │    │   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Host System                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │    Data     │  │    Logs     │  │      FIT Files          │ │
│  │   Volume    │  │   Volume    │  │       Volume            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🌍 Environment Configurations

### Development Environment

**Purpose**: Local development with hot reloading and debugging tools.

```bash
# Deploy development environment
./scripts/deploy.sh -e development deploy

# With additional tools
./scripts/deploy.sh -e development -p tools deploy
```

**Features**:
- ✅ Hot reloading with volume mounts
- ✅ Debug port exposed (5678)
- ✅ Simulator enabled by default
- ✅ Development tools included
- ✅ Relaxed security settings
- ✅ Database viewer (Adminer) available

**Configuration**: Uses `.env` file

### Staging Environment

**Purpose**: Production-like testing environment.

```bash
# Deploy staging environment
./scripts/deploy.sh -e staging deploy

# With test data generation
./scripts/deploy.sh -e staging -p test-data deploy
```

**Features**:
- ✅ Production-like configuration
- ✅ Configurable simulator usage
- ✅ Shorter data retention (30 days)
- ✅ Enhanced logging (DEBUG level)
- ✅ Test data generation tools
- ✅ Separate database and storage

**Configuration**: Uses `.env.staging` file

### Production Environment

**Purpose**: Live production deployment with full security and monitoring.

```bash
# Deploy production (basic)
./scripts/deploy.sh -e production deploy

# Deploy with reverse proxy
./scripts/deploy.sh -e production -p nginx deploy

# Deploy with full monitoring
./scripts/deploy.sh -e production -p nginx,monitoring deploy
```

**Features**:
- ✅ Multi-stage optimized builds
- ✅ Security hardening (non-root user, read-only filesystem)
- ✅ Resource limits and health checks
- ✅ Log rotation and management
- ✅ SSL/TLS support via Nginx
- ✅ Prometheus metrics and Grafana dashboards
- ✅ Automatic backup creation

**Configuration**: Uses `.env` file with production settings

## 🔧 Configuration Management

### Environment Files

| Environment | File | Purpose |
|-------------|------|---------|
| Development | `.env` | Local development settings |
| Staging | `.env.staging` | Staging-specific configuration |
| Production | `.env` | Production settings |

### Configuration Validation

The deployment script automatically validates configuration:

```bash
# Manual validation
python3 scripts/validate-config.py production --env-file .env

# Validation with warnings suppressed
python3 scripts/validate-config.py production --env-file .env --quiet
```

### Key Configuration Variables

#### Required (Production)
- `SECRET_KEY`: Flask secret key (must be unique and secure)

#### Application Settings
- `APP_PORT`: Application port (default: 5000)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `USE_SIMULATOR`: Enable simulator mode (true/false)

#### Database Settings
- `DATABASE_URL`: Database connection string
- `DATA_RETENTION_DAYS`: How long to keep workout data

#### Security Settings
- `API_RATE_LIMIT`: API request rate limiting
- `CONNECTION_TIMEOUT`: Bluetooth connection timeout

#### Monitoring Settings
- `METRICS_ENABLED`: Enable Prometheus metrics
- `PROMETHEUS_PORT`: Prometheus port (default: 9090)
- `GRAFANA_PORT`: Grafana port (default: 3000)

## 🐳 Docker Compose Profiles

Profiles allow you to enable additional services:

### Available Profiles

| Profile | Services | Purpose |
|---------|----------|---------|
| `nginx` | Nginx reverse proxy | SSL termination, load balancing |
| `monitoring` | Prometheus + Grafana | Metrics collection and visualization |
| `tools` | Adminer, test runners | Development and debugging tools |
| `test-data` | Test data generator | Generate sample data for testing |
| `logging` | Log rotation service | Automated log management |

### Usage Examples

```bash
# Basic deployment
./scripts/deploy.sh -e production deploy

# With reverse proxy
./scripts/deploy.sh -e production -p nginx deploy

# Full monitoring stack
./scripts/deploy.sh -e production -p nginx,monitoring deploy

# Development with tools
./scripts/deploy.sh -e development -p tools deploy
```

## 🏥 Health Checks and Monitoring

### Health Check Endpoints

| Endpoint | Purpose | Usage |
|----------|---------|-------|
| `/health` | Basic health check | Docker health checks, load balancers |
| `/health/detailed` | Comprehensive status | Detailed system monitoring |
| `/health/ready` | Readiness probe | Kubernetes readiness checks |
| `/health/live` | Liveness probe | Kubernetes liveness checks |

### Health Check Components

- **Database**: Connection and integrity
- **Bluetooth**: Adapter availability and status
- **Disk Space**: Available storage monitoring
- **Memory**: System and process memory usage
- **Application**: Service responsiveness

### Monitoring Stack (with monitoring profile)

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Node Exporter**: System metrics
- **cAdvisor**: Container metrics

Access URLs (with monitoring profile):
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin)

## 💾 Data Management

### Volume Strategy

#### Development
Uses Docker named volumes for easy cleanup:
```yaml
volumes:
  dev_data: {}
  dev_logs: {}
  dev_fit_files: {}
```

#### Production
Uses bind mounts for data persistence:
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
  - ./fit_files:/app/fit_files
```

### Backup and Recovery

#### Automated Backups
```bash
# Create backup before deployment
./scripts/deploy.sh deploy  # Automatic backup

# Manual backup
./scripts/deploy.sh backup
```

#### Restore from Backup
```bash
# Interactive restore
./scripts/deploy.sh restore

# List available backups
ls -la backups/
```

#### Backup Contents
- Application database
- Configuration files
- FIT files (optional)
- Backup metadata and timestamps

## 🔒 Security Considerations

### Container Security

- **Non-root execution**: Application runs as unprivileged user
- **Read-only filesystem**: Where possible, prevents runtime modifications
- **Resource limits**: CPU and memory constraints
- **Security scanning**: Regular image vulnerability scans

### Network Security

- **Firewall rules**: Restrict access to necessary ports only
- **SSL/TLS**: HTTPS enforcement in production (nginx profile)
- **Rate limiting**: API request throttling
- **CORS protection**: Cross-origin request restrictions

### Data Security

- **Environment variables**: Sensitive data via environment files
- **Database encryption**: SQLite encryption at rest
- **Log sanitization**: No sensitive data in logs
- **Backup encryption**: Encrypted backup storage

### Production Security Checklist

- [ ] Unique SECRET_KEY set
- [ ] Default passwords changed
- [ ] SSL certificates configured
- [ ] Firewall rules applied
- [ ] Regular security updates scheduled
- [ ] Backup encryption enabled
- [ ] Log monitoring configured

## 🚨 Troubleshooting

### Common Issues

#### 1. Bluetooth Access Problems
```bash
# Check Bluetooth adapter
ls /sys/class/bluetooth/

# Verify container privileges
docker-compose ps
# Should show privileged: true

# Check host network mode
# Should use network_mode: host on Linux
```

#### 2. Health Check Failures
```bash
# Check application logs
./scripts/deploy.sh logs

# Manual health check
curl -v http://localhost:5000/health

# Detailed health status
curl http://localhost:5000/health/detailed | jq
```

#### 3. Database Issues
```bash
# Check database file
ls -la data/workouts.db

# Database permissions
docker-compose exec rogue-garmin-bridge ls -la data/

# Database integrity
docker-compose exec rogue-garmin-bridge sqlite3 data/workouts.db "PRAGMA integrity_check;"
```

#### 4. Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :5000

# Change port in environment file
echo "APP_PORT=5001" >> .env

# Redeploy
./scripts/deploy.sh restart
```

#### 5. SSL Certificate Issues (nginx profile)
```bash
# Check certificate files
ls -la nginx/ssl/

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes

# Verify certificate
openssl x509 -in nginx/ssl/cert.pem -text -noout
```

### Log Analysis

```bash
# View all logs
./scripts/deploy.sh logs

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f

# Filter specific service
docker-compose -f docker-compose.prod.yml logs rogue-garmin-bridge

# Search logs for errors
docker-compose -f docker-compose.prod.yml logs | grep -i error
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Monitor system resources
docker-compose exec rogue-garmin-bridge top

# Database performance
docker-compose exec rogue-garmin-bridge sqlite3 data/workouts.db "ANALYZE;"
```

## 🔄 Maintenance and Updates

### Regular Maintenance Tasks

#### Daily
- Monitor health check status
- Review error logs
- Check disk space usage

#### Weekly
- Update Docker images
- Clean up old containers and images
- Review performance metrics

#### Monthly
- Update base system packages
- Review and rotate logs
- Test backup and restore procedures
- Security audit and updates

### Update Procedures

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Update deployment
./scripts/deploy.sh update

# Verify health
./scripts/deploy.sh status
```

#### System Updates
```bash
# Update Docker images
docker-compose pull

# Rebuild with latest base images
./scripts/deploy.sh -e production --build deploy

# Clean up old images
./scripts/deploy.sh cleanup
```

### Monitoring and Alerting

#### Key Metrics to Monitor
- Application response time
- Database query performance
- Memory and CPU usage
- Disk space utilization
- Bluetooth connection stability
- Error rates and patterns

#### Alert Thresholds
- Health check failures: Immediate
- High memory usage: >80%
- Disk space low: <10% free
- High error rate: >5% of requests
- Database connection failures: Immediate

## 📚 Additional Resources

### Documentation
- [Docker Deployment Guide](docs/docker-deployment.md)
- [API Reference](docs/developer-guide/api-reference.md)
- [Troubleshooting Guide](docs/user-guide/troubleshooting.md)

### Scripts and Tools
- `scripts/deploy.sh`: Main deployment script
- `scripts/validate-config.py`: Configuration validation
- `scripts/docker-healthcheck.sh`: Health check script
- `scripts/logrotate.conf`: Log rotation configuration

### Configuration Files
- `docker-compose.prod.yml`: Production deployment
- `docker-compose.staging.yml`: Staging deployment
- `docker-compose.dev.yml`: Development deployment
- `monitoring/prometheus.yml`: Metrics configuration
- `nginx/nginx.conf`: Reverse proxy configuration

## 🆘 Support

For issues and questions:

1. **Check Health Status**: `curl http://localhost:5000/health/detailed`
2. **Review Logs**: `./scripts/deploy.sh logs`
3. **Validate Configuration**: `python3 scripts/validate-config.py production`
4. **Check Documentation**: Review relevant docs in `docs/` directory
5. **GitHub Issues**: Create issue with logs and configuration details

### Getting Help

When reporting issues, please include:
- Environment (development/staging/production)
- Docker and Docker Compose versions
- Configuration file (with sensitive data removed)
- Application logs
- Health check output
- Steps to reproduce the issue

---

**Happy Deploying! 🚀**